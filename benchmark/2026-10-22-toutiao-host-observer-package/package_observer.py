#!/usr/bin/env python3
"""T41: assemble + sign the passive host-observer HAP from the accepted b189 base. No device/install.

Base = the T32/T33-accepted candidate HAP b18978b8... (54215 B). The ONLY content change is
ets/entryability/EntryAbility.abc: bb1eccd3... -> the T40-compiled db781436... . The other 8 ZIP members
(including .pages.info, Index 3d98dbfb, module, icons, resources) are kept byte-for-byte; a member-level
change of anything but EntryAbility is refused. The original public dev certificate/profile and identity are
reused (no new identity/permission/credential). java and signer SHAs are HARD-verified (not just recorded).

All personal absolute paths are passed as args (nothing hard-coded). Full argv (which contains the pinned
public dev keystore password) and stderr go ONLY to the private raw dir; the public out dir gets redacted
argv + rc + time + the SHA of each private raw file. Every VM/tool command records argv/rc/start/end and
catches OSError (rc 125, separate driver-error). A nonzero rc / assertion / drift stops with an explicit
FAILED receipt; the out dirs must not already exist; no reroute, no device, no T38.
"""
import argparse, hashlib, json, shutil, struct, subprocess, sys, time, zipfile
from pathlib import Path
sys.dont_write_bytecode = True

BASE_SHA = 'b18978b875098bc66f1ee78e471ef64c7899978bf46052502c41801f168e9ff0'
BASE_BYTES = 54215
ENTRY = 'ets/entryability/EntryAbility.abc'
META = '.pages.info'                 # executable-page bitmap, NOT a generic resource; signer-derived per ABC page layout
EXC_FILE = Path(__file__).resolve().parent / 't41-metadata-exception.json'
EXC_SHA = '282d07030b0977a5a4c7a6e4375b6d5af1f6a04484af2a1429462f27569beab3'  # my copy == master 5f80adf44 blob
PAGE = 4096                          # PageInfoExtension page size; DEFAULT_UNIT_SIZE=4 -> bit index = page*4+1
BASE_MEMBERS = {
    ENTRY: 'bb1eccd3338dde573393b24d81e26e67450d5461ba51f73e578d9e42a78cbde9',
    'ets/pages/Index.abc': '3d98dbfb8a8cf35197c489c3af11285800ea9d2be877786d18bb2ae8f14a0fd3',
    '.pages.info': '9e217e6bf2942339c6a48480fa7eab0aac43a96e4fcb21c62b8a37d52d00c301',
    'ResourceTable.txt': '08f6d29206cfd62fd3781e273cedacfda6a1289d8f1bac9164d26b7dfa5624cc',
    'module.json': '0dbaacbe6b17eadecda308d65e77483bf87fe2971695fecac1a5b55a5d137b51',
    'resources.index': 'bc5b097d1f2db578797a070f470e0907b2e1dfd655d18ab3778a8c5cd93051b5',
    'resources/base/media/app_icon.png': 'c2c6eeaa38c5499f0bf173d1454459dfb300b052f76415ee8b5e129bdc399223',
    'resources/base/media/icon.png': 'c2c6eeaa38c5499f0bf173d1454459dfb300b052f76415ee8b5e129bdc399223',
    'resources/base/profile/main_pages.json': '621d1c271cf89755a64364b8e70c65745d9049ebaf18efa3eba95a2ae0b4558d'}
REPL_SHA = 'db7814368150e9a90b39c77fb5762802ce033b1bccb43a53e719720516b59bdd'
JAVA_SHA = 'd7ab2ea6a7e731a8a2cee7d722046c9f7d8c5f184cd769b9954a392592337770'
SIGNER_SHA = '91cea67369a8389e0cec60ebac6f2382d157515b9d96b0ef36b60b86ca528e9b'
PROFILE_SHA = '87743d711ff7bbec6995e262357593bcbb08bc77cf90169ce463436da52cc623'
CERT_CHAIN_SHA = '5358faac7e78e3d89755a0b5da6c0ffe847c66f8dec02cce313e1f4b1b867de4'
PUBLIC_SIGNING = {'OpenHarmony.p12': '7a5efc3ea9245596d157f6ccbbdc5b8ae7cd714e7086c3c1645986c9d495d071',
    'OpenHarmonyApplication.pem': 'b5c1d6254faa91eab645a32fc3ce136128c94d88a739a0e956e6a49b331387e5',
    'OpenHarmonyProfileRelease.pem': '515f0bd8173fabb8bf8f146cd61207baa0e2d6ab8693ae7623df7ee6f16af70e',
    'UnsgnedReleasedProfileTemplate.json': '5ee5a8ee4cde5586b9ec20dc0405d1ee71a7c7d95cbfdb18926e30418619e343'}

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def _data_offset(hap, info):
    with open(hap, 'rb') as f:
        f.seek(info.header_offset)
        need(f.read(4) == b'PK\x03\x04', 'LOCAL_HEADER', 'bad local header')
        f.seek(info.header_offset + 26); fn, ex = struct.unpack('<HH', f.read(4))
    return info.header_offset + 30 + fn + ex
def abc_pages(hap):
    """Independently parse ZIP local headers; return {abc_name: {offset,bytes,pages}} for .abc members only."""
    out = {}
    with zipfile.ZipFile(hap) as z:
        for i in z.infolist():
            if i.filename.endswith('.abc'):
                off = _data_offset(hap, i); n = i.file_size
                pages = list(range(off // PAGE, (off + n - 1) // PAGE + 1)) if n else []
                out[i.filename] = {'offset': off, 'bytes': n, 'pages': pages}
    return out
def page_bitmap(hap):
    """Reconstruct the 8-byte LE executable-page bitmap from the ABC page occupancy (bit = page*4+1)."""
    bits = bytearray(8)
    for e in abc_pages(hap).values():
        for pg in e['pages']:
            idx = pg * 4 + 1; bits[idx // 8] |= 1 << (idx % 8)
    return bytes(bits)
def digest(b): return hashlib.sha256(b).hexdigest()

class Stop(Exception):
    def __init__(self, status, msg): self.status, self.msg = status, msg
def need(c, status, msg):
    if not c: raise Stop(status, msg)

def payload(path):
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        need(len(names) == len(set(names)), 'DUPLICATE_MEMBERS', 'duplicate ZIP members')
        need(all(not n.startswith('/') and '..' not in Path(n).parts for n in names), 'UNSAFE_MEMBER', 'unsafe member')
        return {n: z.read(n) for n in names}

def alias_path(p):
    """Home-relative alias that FULLY preserves the tail (incl .local); non-HOME paths get no guessed prefix."""
    rp = Path(p).resolve()
    try: return '$HOME/' + rp.relative_to(Path.home()).as_posix()
    except ValueError: return None  # caller must supply an explicit alias; never guess a prefix

def redact(argv, amap):
    """Public argv: mask password tokens AND replace known absolute paths with explicit role aliases.
    amap maps an exact resolved path string -> alias. Any other '/'-absolute token is home-relative
    aliased when under HOME, else emitted as <abs-path-redacted> rather than leaking a guessed prefix."""
    out, skip = [], False
    for t in argv:
        t = str(t)
        if skip: out.append('<redacted-secret>'); skip = False; continue
        if t in ('-keyPwd', '-keystorePwd') or t.lower().endswith('pwd'): out.append(t); skip = True; continue
        if t in amap: out.append(amap[t]); continue
        if t.startswith('/'):
            a = alias_path(t); out.append(a if a is not None else '<abs-path-redacted>'); continue
        out.append(t)
    return out

def verify_candidate(base_hap, signed_hap, before, after, signer_sha, exc_file=EXC_FILE):
    """Production post-sign check (shared by driver and checker). Strict program/resource criterion:
    EntryAbility is the only CONTENT change; the other 7 program/resource members byte-identical;
    .pages.info permitted ONLY under the single SHA-pinned exact exception AND independent page-bitmap
    derivation reproducing both actual 8-byte bitmaps. Anything else changing -> Stop. Not a generic
    signing-metadata exemption. Raises Stop on any violation; returns the exception/member record."""
    need(set(after) == set(before), 'MEMBER_SET', 'signed member set')
    changed = sorted(n for n in before if before[n] != after[n])
    need(digest(after[ENTRY]) == REPL_SHA, 'SIGNED_ENTRY', 'signed EntryAbility SHA')
    seven = sorted(set(before) - {ENTRY, META})
    need(len(seven) == 7, 'MEMBER_MODEL', '7 program/resource members expected')
    drifted7 = [n for n in seven if before[n] != after[n]]
    need(drifted7 == [], 'UNEXPECTED_RESOURCE_CHANGE', str(drifted7))
    need(set(changed) <= {ENTRY, META}, 'UNEXPECTED_SIGNED_CHANGE', str(changed))
    exc = json.loads(Path(exc_file).read_text())
    need(sha(exc_file) == EXC_SHA, 'EXCEPTION_FILE_SHA', 'exception file drift')
    need(exc['member'] == META and exc['signer_sha256'] == signer_sha, 'EXCEPTION_SCOPE', 'exception scope/signer')
    need(digest(before[META]) == exc['before_sha256'] and before[META].hex() == exc['before_hex'], 'META_BEFORE', 'base .pages.info != exception before')
    need(digest(after[META]) == exc['after_sha256'] and after[META].hex() == exc['after_hex'], 'META_AFTER', 'signed .pages.info != exception after')
    der_before = page_bitmap(base_hap); der_after = page_bitmap(signed_hap)
    need(der_before == before[META], 'DERIVE_BEFORE', 'derived base bitmap != actual')
    need(der_after == after[META], 'DERIVE_AFTER', 'derived signed bitmap != actual')
    need(der_before == bytes.fromhex(exc['before_hex']) and der_after == bytes.fromhex(exc['after_hex']), 'DERIVE_EXC', 'derivation != exception hex')
    return {'seven': seven, 'changed': changed, 'der_before': der_before, 'der_after': der_after,
            'meta_changed': before[META] != after[META]}

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for n in ('base', 'replacement', 'java', 'signer', 'signing-dist', 'out-public', 'out-private', 'pwd-file'):
        ap.add_argument('--' + n, required=True)
    a = ap.parse_args()
    pub = Path(a.out_public).expanduser().resolve(); prv = Path(a.out_private).expanduser().resolve()
    for d in (pub, prv):
        try: d.mkdir(parents=True, exist_ok=False)
        except FileExistsError:
            print(json.dumps({'status': 'OUT_DIR_EXISTS_REFUSED', 'dir': str(d)}), file=sys.stderr); sys.exit(2)
    (pub / 'raw-public').mkdir(); (prv / 'raw').mkdir()
    rc = {'status': 'INCOMPLETE', 'device_calls': 0, 'deployment_accepted': False,
          'base': {'sha256': BASE_SHA, 'bytes': BASE_BYTES}, 'replacement_entryability_sha256': REPL_SHA,
          'tools': {}, 'commands': []}
    def save(): (pub / 'receipt.json').write_text(json.dumps(rc, indent=2) + '\n')
    save()
    java, signer, dist = Path(a.java), Path(a.signer), Path(a.signing_dist)
    pwd = Path(a.pwd_file).read_text().strip()                       # private keystore pwd; never printed/committed
    need(pwd != '', 'EMPTY_PWD_FILE', 'pwd-file empty')
    amap = {str(java.resolve()): '<java>', str(signer.resolve()): '<signer>', str(Path(a.base).resolve()): '<base.hap>',
            str(Path(a.replacement).resolve()): '<replacement-EntryAbility.abc>', str(dist.resolve()): '<signing-dist>',
            str(pub): '<out-public>', str(prv): '<out-private>'}
    for n in PUBLIC_SIGNING: amap[str((dist / n).resolve())] = f'<signing-dist>/{n}'
    def run(tag, args):
        argv = [str(java.resolve()), '-jar', str(signer.resolve())] + [str(x) for x in args]
        (prv / 'raw' / f'{tag}.argv.json').write_text(json.dumps(argv, indent=2) + '\n')           # private: full argv (incl pwd)
        (pub / 'raw-public' / f'{tag}.argv.redacted.json').write_text(json.dumps(redact(argv, amap), indent=2) + '\n')
        st = time.time(); r = None; err = None
        try:
            with (prv / 'raw' / f'{tag}.stdout').open('wb') as o, (prv / 'raw' / f'{tag}.stderr').open('wb') as e:
                r = subprocess.run(argv, stdout=o, stderr=e, timeout=180).returncode
        except subprocess.TimeoutExpired:
            r = 124; err = f'local timeout 180s; does not prove tool exit; not retried'
        except OSError as ex:
            r = 125; err = f'OSError: {ex!r}'
        for name in (f'{tag}.stdout', f'{tag}.stderr'):
            if not (prv / 'raw' / name).exists(): (prv / 'raw' / name).write_bytes(b'')
        (prv / 'raw' / f'{tag}.rc').write_text(str(r) + '\n')
        (prv / 'raw' / f'{tag}.time.json').write_text(json.dumps({'start': st, 'end': time.time()}) + '\n')
        if err: (prv / 'raw' / f'{tag}.driver-error.txt').write_text(err + '\n')
        rc['commands'].append({'tag': tag, 'rc': r, **({'driver_error': err} if err else {})}); save()
        need(r == 0, 'COMMAND_FAILED', f'{tag} rc={r}')
    try:
        # hard input checks (not just recorded)
        need(java.is_file() and sha(java) == JAVA_SHA, 'JAVA_SHA', 'java SHA/channel')
        need(signer.is_file() and sha(signer) == SIGNER_SHA, 'SIGNER_SHA', 'signer SHA/channel')
        for n, h in PUBLIC_SIGNING.items(): need((dist / n).is_file() and sha(dist / n) == h, 'PUBLIC_SIGNING_SHA', n)
        rc['tools'] = {'java_sha256': sha(java), 'signer_sha256': sha(signer)}; save()
        need(sha(a.base) == BASE_SHA and Path(a.base).stat().st_size == BASE_BYTES, 'BASE_SHA', 'base HAP SHA/size')
        before = payload(a.base)
        need({n: digest(b) for n, b in before.items()} == BASE_MEMBERS, 'BASE_MEMBERS', 'base members')
        need(sha(a.replacement) == REPL_SHA, 'REPLACEMENT_SHA', 'replacement EntryAbility SHA')
        shutil.copyfile(a.base, pub / 'base.hap')
        run('verify-base', ['verify-app', '-inFile', pub / 'base.hap', '-outCertChain', pub / 'original.cer', '-outProfile', pub / 'original.p7b'])
        need(sha(pub / 'original.p7b') == PROFILE_SHA, 'EXTRACTED_PROFILE', 'extracted profile drift')
        need(sha(pub / 'original.cer') == CERT_CHAIN_SHA, 'ORIGINAL_CERT_CHAIN', 'cert chain drift')
        run('verify-profile', ['verify-profile', '-inFile', pub / 'original.p7b', '-outFile', pub / 'profile-verified.json'])
        need(json.loads((pub / 'profile-verified.json').read_text())['verifiedPassed'] is True, 'PROFILE_VERIFICATION', 'profile not verified')
        repl = Path(a.replacement).read_bytes()
        unsigned = pub / 'candidate-unsigned.hap'
        with zipfile.ZipFile(unsigned, 'x', zipfile.ZIP_STORED) as z:
            for n, b in sorted(before.items()):
                item = zipfile.ZipInfo(n, (1980, 1, 1, 0, 0, 0)); item.create_system = 3; item.external_attr = 0o100644 << 16
                z.writestr(item, repl if n == ENTRY else b)
        un = payload(unsigned)
        need(set(un) == set(before), 'MEMBER_SET', 'unsigned member set')
        need(un[ENTRY] == repl and digest(un[ENTRY]) == REPL_SHA, 'UNSIGNED_ENTRY', 'unsigned EntryAbility')
        chg = sorted(n for n in before if before[n] != un[n])
        need(chg == [ENTRY], 'UNEXPECTED_UNSIGNED_CHANGE', str(chg))
        run('sign-candidate', ['sign-app', '-mode', 'localSign', '-keyAlias', 'openharmony application release',
            '-appCertFile', dist / 'OpenHarmonyApplication.pem', '-profileFile', pub / 'original.p7b',
            '-inFile', unsigned, '-outFile', pub / 'candidate-signed.hap', '-compatibleVersion', '20',
            '-signCode', '1', '-signAlg', 'SHA256withECDSA', '-keystoreFile', dist / 'OpenHarmony.p12',
            '-keyPwd', pwd, '-keystorePwd', pwd])
        run('verify-candidate', ['verify-app', '-inFile', pub / 'candidate-signed.hap', '-outCertChain', pub / 'candidate.cer', '-outProfile', pub / 'candidate.p7b'])
        need((pub / 'candidate.cer').read_bytes() == (pub / 'original.cer').read_bytes(), 'CERTIFICATE_DRIFT', 'cert chain changed')
        need((pub / 'candidate.p7b').read_bytes() == (pub / 'original.p7b').read_bytes(), 'PROFILE_DRIFT', 'profile changed')
        after = payload(pub / 'candidate-signed.hap')
        rec = verify_candidate(pub / 'base.hap', pub / 'candidate-signed.hap', before, after, rc['tools']['signer_sha256'])
        seven, changed, der_before, der_after, meta_changed = (
            rec['seven'], rec['changed'], rec['der_before'], rec['der_after'], rec['meta_changed'])
        rc.update(status='OFFLINE_SIGNED_CANDIDATE_VERIFIED_NOT_DEPLOYED',
            content_change_members=[ENTRY], seven_program_resource_members_unchanged=seven,
            signed_changed_members=changed,
            pages_info_exception={'member': META, 'applied': meta_changed, 'exception_file': str(EXC_FILE.relative_to(Path.cwd())) if str(EXC_FILE).startswith(str(Path.cwd())) else EXC_FILE.name,
                'exception_file_sha256': EXC_SHA, 'before_hex': before[META].hex(), 'after_hex': after[META].hex(),
                'derived_before_hex': der_before.hex(), 'derived_after_hex': der_after.hex(),
                'independent_derivation_matches_actual': True,
                'base_abc_pages': {k: v['pages'] for k, v in abc_pages(pub / 'base.hap').items()},
                'candidate_abc_pages': {k: v['pages'] for k, v in abc_pages(pub / 'candidate-signed.hap').items()}},
            members={n: {'before_sha256': digest(before[n]), 'after_sha256': digest(after[n])} for n in sorted(before)},
            artifacts={n: {'sha256': sha(pub / n), 'bytes': (pub / n).stat().st_size}
                       for n in ('base.hap', 'candidate-unsigned.hap', 'candidate-signed.hap', 'original.cer', 'candidate.cer', 'original.p7b', 'candidate.p7b')},
            signature_container={'base_hap_sha256': BASE_SHA, 'signed_hap_sha256': sha(pub / 'candidate-signed.hap'),
                                 'note': 'whole-HAP SHA differs by the signature container; member payload differs only in EntryAbility'},
            private_raw_pins={(alias_path(f) or amap.get(str(f.resolve())) or '<abs-path-redacted>/' + f.name): sha(f)
                              for f in sorted((prv / 'raw').iterdir())})
        save()
    except Stop as s:
        rc['status'] = s.status; rc['stop_reason'] = s.msg; save()
        print(json.dumps({'status': s.status, 'reason': s.msg}), file=sys.stderr); sys.exit(1)
    print(json.dumps(rc, indent=2))

if __name__ == '__main__':
    main()
