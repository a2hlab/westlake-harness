#!/usr/bin/env python3
"""T41 production check: verify the offline host-observer package is EntryAbility-only (+ the single
exact derived .pages.info metadata exception) with real code, not a self-asserting helper.

Positive path runs the SHARED production verifier (package_observer.verify_candidate) against the real
persisted release HAPs and re-derives the 8-byte executable-page bitmap independently (and purely, from
the receipt's recorded ABC page layout). Negatives drive that SAME production verifier against mutated
payloads (an extra resource member changed; EntryAbility not the T40 ABC; a generic .pages.info drift;
.pages.info matching the exception hex but NOT reproduced by the actual ABC page layout; a tampered
exception file; a foreign signer scope; a changed member set) and drive the real driver to refuse a
reused output dir / missing args. No device, no REA, no signing is performed by this checker.
"""
import argparse, copy, importlib.util, json, os, subprocess, sys, tempfile
from pathlib import Path
sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
DRIVER = HERE / 'package_observer.py'
EXC_FILE = HERE / 't41-metadata-exception.json'
_spec = importlib.util.spec_from_file_location('pkg', DRIVER)
pkg = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(pkg)
ENTRY, META, REPL_SHA, EXC_SHA = pkg.ENTRY, pkg.META, pkg.REPL_SHA, pkg.EXC_SHA

def bitmap_from_pages(pagemap):
    """Pure arithmetic reproduction of bit(page*4+1), independent of any HAP; catches a forged receipt."""
    bits = bytearray(8)
    for pages in pagemap.values():
        for pg in pages:
            i = pg * 4 + 1; bits[i // 8] |= 1 << (i % 8)
    return bytes(bits)

STAGES = ('verify-base', 'verify-profile', 'sign-candidate', 'verify-candidate')

def resolve_alias(alias):
    """Map a receipt alias back to its real path. Only $HOME/~ aliases are resolvable here; role
    aliases like <out-private> are not a raw-record location and return None (treated as missing)."""
    if alias.startswith('$HOME/'): return Path.home() / alias[len('$HOME/'):]
    if alias.startswith('~'): return Path(os.path.expanduser(alias))
    return None

def verify_evidence(receipt, build_dir, resolver):
    """Complete acceptance: every receipt.artifacts file and every private_raw_pins record must exist on
    disk with the pinned sha256 (and size for artifacts), and the 4 signing stages must have rc==0 with a
    parseable time record. Any missing/mismatched evidence raises pkg.Stop (nonzero exit). Not self-assert:
    it re-hashes the real artifacts and raw originals."""
    import hashlib
    for name, meta in receipt['artifacts'].items():
        f = build_dir / name
        pkg.need(f.is_file(), 'ARTIFACT_MISSING', name)
        b = f.read_bytes()
        pkg.need(hashlib.sha256(b).hexdigest() == meta['sha256'] and len(b) == meta['bytes'], 'ARTIFACT_SHA', name)
    pins = receipt['private_raw_pins']
    for alias, h in pins.items():
        f = resolver(alias)
        pkg.need(f is not None and f.is_file(), 'RAW_MISSING', alias)
        pkg.need(hashlib.sha256(f.read_bytes()).hexdigest() == h, 'RAW_SHA', alias)
    for tag in STAGES:
        rc = [resolver(a) for a in pins if a.endswith(f'{tag}.rc')]
        tm = [resolver(a) for a in pins if a.endswith(f'{tag}.time.json')]
        pkg.need(len(rc) == 1 and len(tm) == 1, 'RAW_STAGE', tag)
        pkg.need(rc[0].read_text().strip() == '0', 'RAW_RC', tag)
        t = json.loads(tm[0].read_text()); pkg.need('start' in t and 'end' in t, 'RAW_TIME', tag)
    return {'artifacts': len(receipt['artifacts']), 'raw_records': len(pins), 'stages_rc0_timed': len(STAGES)}

def refuses(status, fn):
    try: fn()
    except pkg.Stop as e:
        if e.status != status: raise AssertionError(f'expected Stop {status}, got {e.status} ({e.msg})')
        return {'case_status': status, 'msg': e.msg}
    raise AssertionError(f'production verifier accepted what should raise {status}')

def driver_exit(code, args):
    r = subprocess.run([sys.executable, '-I', str(DRIVER)] + args, capture_output=True, text=True)
    if r.returncode != code: raise AssertionError(f'driver expected exit {code}, got {r.returncode}: {r.stderr[-200:]}')
    return r.returncode

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--require-raw', action='store_true', help='force complete-evidence mode even without on-disk artifacts')
    ap.add_argument('--build-dir', type=Path,
                    default=Path(os.path.expanduser('~/.local/share/westlake/toutiao-host-observer-package-20261022/release-02')))
    a = ap.parse_args()
    bd = a.build_dir
    # committed, device-free structural + pure-derivation checks (always run)
    assert pkg.sha(EXC_FILE) == EXC_SHA, 'exception file drift vs pinned master blob'
    exc = json.loads(EXC_FILE.read_text())
    assert exc['member'] == META and exc['bytes'] == 8, 'exception member/size'
    receipt = json.loads((HERE / 'receipt' / 'receipt.json').read_text())
    assert receipt['status'] == 'OFFLINE_SIGNED_CANDIDATE_VERIFIED_NOT_DEPLOYED', 'status'
    assert receipt['device_calls'] == 0 and receipt['deployment_accepted'] is False, 'device/deploy claim'
    assert receipt['content_change_members'] == [ENTRY], 'content change not EntryAbility-only'
    assert len(receipt['seven_program_resource_members_unchanged']) == 7, 'seven-member model'
    assert sorted(receipt['signed_changed_members']) == sorted([ENTRY, META]), 'signed change set'
    assert [c['rc'] for c in receipt['commands']] == [0, 0, 0, 0], 'signing stage rc'
    e = receipt['pages_info_exception']
    assert e['applied'] is True and e['independent_derivation_matches_actual'] is True, 'exception/derivation flag'
    assert bitmap_from_pages(e['base_abc_pages']).hex() == exc['before_hex'] == e['before_hex'], 'base bitmap reproduction'
    assert bitmap_from_pages(e['candidate_abc_pages']).hex() == exc['after_hex'] == e['after_hex'], 'candidate bitmap reproduction'
    # the committed redacted argv must carry no secret and no raw user path
    for f in sorted((HERE / 'receipt' / 'raw-public').glob('*.redacted.json')):
        txt = f.read_text()
        assert '123456' not in txt and '/Users/' not in txt, f'public argv leak in {f.name}'

    negatives, evidence, mode = [], None, 'receipt-only'
    base_hap, signed_hap = bd / 'base.hap', bd / 'candidate-signed.hap'
    artifacts_present = base_hap.is_file() and signed_hap.is_file()
    complete_required = a.require_raw or artifacts_present   # a real build on disk DEMANDS complete verification
    if complete_required:
        mode = 'complete'
        # scenario 3: missing/tampered artifacts or raw originals -> nonzero (re-hash the real files)
        evidence = verify_evidence(receipt, bd, resolve_alias)
        before, after = pkg.payload(base_hap), pkg.payload(signed_hap)
        signer_sha = receipt['tools']['signer_sha256']
        # POSITIVE: the real shared production verifier accepts the real build
        ok = pkg.verify_candidate(base_hap, signed_hap, before, after, signer_sha)
        assert ok['changed'] == sorted([ENTRY, META]) and ok['meta_changed'] is True, 'positive verify'
        assert ok['der_before'].hex() == exc['before_hex'] and ok['der_after'].hex() == exc['after_hex'], 'positive derivation'
        # real cert/profile identity before==after
        assert (bd / 'original.cer').read_bytes() == (bd / 'candidate.cer').read_bytes(), 'cert drift'
        assert (bd / 'original.p7b').read_bytes() == (bd / 'candidate.p7b').read_bytes(), 'profile drift'
        def mut(**kw):
            d = copy.deepcopy(after); d.update(kw); return d
        tampered = Path(tempfile.mkdtemp()) / 'exc.json'; tampered.write_text(EXC_FILE.read_text() + ' ')
        V = lambda **k: pkg.verify_candidate(base_hap, signed_hap, before, k.get('after', after), k.get('signer', signer_sha), k.get('exc', EXC_FILE))
        negatives = [
            ('extra resource member changed', 'UNEXPECTED_RESOURCE_CHANGE', lambda: pkg.verify_candidate(base_hap, signed_hap, before, mut(**{'module.json': after['module.json'] + b'x'}), signer_sha)),
            ('EntryAbility not the T40 ABC', 'SIGNED_ENTRY', lambda: pkg.verify_candidate(base_hap, signed_hap, before, mut(**{ENTRY: before[ENTRY]}), signer_sha)),
            ('generic .pages.info drift', 'META_AFTER', lambda: pkg.verify_candidate(base_hap, signed_hap, before, mut(**{META: b'\x00' * 8}), signer_sha)),
            ('.pages.info hex ok but layout not reproduced', 'DERIVE_AFTER', lambda: pkg.verify_candidate(base_hap, base_hap, before, after, signer_sha)),
            ('member added/removed', 'MEMBER_SET', lambda: pkg.verify_candidate(base_hap, signed_hap, before, {k: v for k, v in after.items() if k != 'resources/base/media/icon.png'}, signer_sha)),
            ('tampered exception file', 'EXCEPTION_FILE_SHA', lambda: pkg.verify_candidate(base_hap, signed_hap, before, after, signer_sha, tampered)),
            ('foreign signer scope', 'EXCEPTION_SCOPE', lambda: pkg.verify_candidate(base_hap, signed_hap, before, after, '0' * 64)),
        ]
        negatives = [{'case': n, **refuses(st, fn)} for n, st, fn in negatives]
        # production negative: a deleted/hash-changed real raw log must make complete verification refuse
        import shutil as _sh
        sand = Path(tempfile.mkdtemp())
        for alias in receipt['private_raw_pins']:
            src = resolve_alias(alias); _sh.copyfile(src, sand / src.name)
        victim = sand / resolve_alias(next(a for a in receipt['private_raw_pins'] if a.endswith('sign-candidate.stdout'))).name
        victim.write_bytes(victim.read_bytes() + b'TAMPER')
        negatives.append({'case': 'hash-changed real raw log', **refuses('RAW_SHA',
            lambda: verify_evidence(receipt, bd, lambda al: sand / Path(al).name))})
    # driver-level refusals that need no signing tools (reused out dir; missing args)
    existing = Path(tempfile.mkdtemp())
    drv = [
        ('reused output dir refused', lambda: driver_exit(2, ['--base', str(base_hap), '--replacement', 'x', '--java', 'x',
            '--signer', 'x', '--signing-dist', 'x', '--pwd-file', 'x', '--out-public', str(existing), '--out-private', str(Path(tempfile.mkdtemp()) / 'np')])),
        ('missing required args refused', lambda: driver_exit(2, [])),
    ]
    drv = [{'case': n, 'driver_exit': fn()} for n, fn in drv]
    print(json.dumps({'status': 'PASS', 'mode': mode, 'complete_acceptance': mode == 'complete', 'evidence': evidence, 'device_calls': 0, 'rea_calls': 0, 'signing_in_checker': False,
        'content_change_members': [ENTRY], 'seven_program_resource_unchanged': True,
        'pages_info_exact_exception': True, 'independent_page_bitmap_reproduced': True,
        'generic_pages_info_allowance': False, 'cert_profile_identical': mode == 'complete',
        'production_negatives': negatives, 'driver_refusals': drv}, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
