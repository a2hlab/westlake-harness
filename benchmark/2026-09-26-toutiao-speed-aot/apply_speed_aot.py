"""Offline additive speed-AOT overlay. Never changes native libraries or run.sh.

Requires an unpacked, stopped operator runtime, its framework report, and the
pinned #42 speed bundle. Stage BCP/boot/APK/current A1 libart are read and hashed.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

HERE = Path(__file__).resolve().parent

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def inside(root, rel):
    p = root/rel
    if Path(rel).is_absolute() or '..' in Path(rel).parts: raise ValueError('Invalid relative path')
    for component in [p, *p.parents]:
        if component == root: break
        if component.is_symlink(): raise ValueError('Symlink refused: '+str(component))
    if not p.resolve().is_relative_to(root): raise ValueError('Outside stage')
    return p

def validate(stage, bundle, report, lock):
    files = report.get('files', report.get('source_files', {}))
    required = {k:v['sha256'] for k,v in lock['inputs'].items()}
    for name, expected in required.items():
        if files.get(name, {}).get('sha256') != expected: raise ValueError('Framework report mismatch: '+name)
    # Old framework report predates the A1 native-only overlay. Actual libart must
    # match the separately audited A1 hash, not the historical report's old hash.
    required.update({'libart.so':lock['libart_sha256'], 'toutiao.apk':lock['apk_sha256']})
    for name, expected in required.items():
        if sha(inside(stage, name)) != expected: raise ValueError('Actual runtime mismatch: '+name)
    run = inside(stage, 'run.sh')
    text = run.read_text()
    import re, shlex
    apk = re.findall(r'^export ASX_APK_PATH=(.*)$', text, re.M)
    if len(apk) != 1 or shlex.split(apk[0]) != [lock['dex_location']]:
        raise ValueError('APK logical location differs')
    for name, entry in lock['artifacts'].items():
        if sha(bundle/name) != entry['sha256']: raise ValueError('Artifact SHA mismatch: '+name)
    return required

def atomic_copy(source, target, expected, owner):
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix='.speed-', delete=False) as out:
        temp = Path(out.name)
        try:
            with source.open('rb') as src: shutil.copyfileobj(src, out, 1024*1024)
            out.flush(); os.fchmod(out.fileno(), 0o644)
            if os.geteuid() == 0: os.fchown(out.fileno(), *owner)
            os.fsync(out.fileno())
            if sha(temp) != expected: raise ValueError('Copy checksum mismatch')
            os.replace(temp, target)
        finally:
            if temp.exists(): temp.unlink()

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage', type=Path)
    p.add_argument('--framework-report', type=Path, required=True)
    p.add_argument('--bundle', type=Path, default=Path.home()/'a2hlab/ws/out-aot42/speed-explicit')
    p.add_argument('--dry-run', action='store_true')
    a = p.parse_args()
    if a.stage.is_symlink(): raise ValueError('Symlink stage refused')
    stage = a.stage.resolve(strict=True)
    lock = json.loads((HERE/'speed-lock.json').read_text())
    report = json.loads(a.framework_report.read_text())
    required = validate(stage, a.bundle, report, lock)
    targets = {name:inside(stage, 'oat/arm64/'+name) for name in lock['artifacts']}
    # Existing different AOT may be another experiment; never silently replace it.
    for name, target in targets.items():
        if target.exists() and sha(target) != lock['artifacts'][name]['sha256']:
            raise ValueError('Conflicting AOT: '+str(target)+'; select a fresh runtime')
    if a.dry_run:
        print(json.dumps(dict(inputs_verified=len(required), artifacts=lock['artifacts']), indent=2)); return
    state = inside(stage, '.speed-aot'); state.mkdir(exist_ok=True)
    with inside(stage, '.speed-aot/apply.lock').open('a') as gate:
        fcntl.flock(gate, fcntl.LOCK_EX)
        validate(stage, a.bundle, report, lock)
        owner_stat = (stage/'toutiao.apk').stat(); owner = (owner_stat.st_uid, owner_stat.st_gid)
        for rel in ('oat', 'oat/arm64'):
            folder = inside(stage, rel)
            if not folder.exists():
                folder.mkdir(mode=0o755)
                os.chmod(folder, 0o755)
                if os.geteuid() == 0: os.chown(folder, *owner)
        for name, target in targets.items():
            expected = lock['artifacts'][name]['sha256']
            if target.exists():
                if sha(target) != expected: raise ValueError('Concurrent conflicting AOT')
            else: atomic_copy(a.bundle/name, target, expected, owner)
            if sha(target) != expected: raise ValueError('Installed SHA mismatch')
            print('VERIFIED', expected, target.relative_to(stage))
        sums = ''.join(lock['artifacts'][n]['sha256']+'  oat/arm64/'+n+'\n' for n in sorted(targets))
        receipt = dict(format=1,framework_report_sha256=sha(a.framework_report),
                       speed_lock_sha256=sha(HERE/'speed-lock.json'),inputs=required,
                       artifacts=lock['artifacts'],device_accepted=False,performance_verified=False)
        for name, content in [('SHA256SUMS', sums),('receipt.json', json.dumps(receipt,sort_keys=True,indent=2)+'\n')]:
            dest = inside(stage, '.speed-aot/'+name)
            if not dest.exists() or dest.read_text() != content:
                with tempfile.NamedTemporaryFile(dir=state, delete=False) as tmp:
                    tmp.write(content.encode()); tmp.flush(); os.fsync(tmp.fileno())
                    os.chmod(tmp.name, 0o644); os.replace(tmp.name, dest)
        print('READY_FOR_DEVICE_VALIDATION', state/'receipt.json')

if __name__ == '__main__': main()
