"""Apply pinned #46 artifacts to a LOCAL, stopped ability38 runtime staging tree.

Never invokes HDC or writes a sysctl. A separate privileged launch wrapper does
the latter on the destination device. Unknown binary baselines are refused.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import stat
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent
CHECK = '/system/bin/sh /data/local/tmp/asx/stability46/prelaunch_map_count.sh --check || exit $?'

def digest(data): return hashlib.sha256(data).hexdigest()

def confined(root, relative):
    path = root/relative
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('Nonrelative destination: '+relative)
    for p in [path, *path.parents]:
        if p == root: break
        if p.is_symlink(): raise ValueError('Symlink destination refused: '+str(p))
    if not path.resolve().is_relative_to(root): raise ValueError('Destination escapes stage')
    return path

def rewrite_run(data, targets):
    text = data.decode()
    if '\r' in text or not text.startswith('#!'): raise ValueError('Expected LF shell script with shebang')
    runtime = re.findall(r'^export WESTLAKE_RUNTIME_ROOT=(.*)$', text, re.M)
    if len(runtime) != 1 or shlex.split(runtime[0]) != ['/data/local/tmp/asx']:
        raise ValueError('Expected ability38 /data/local/tmp/asx runtime')
    pattern = re.compile(r'^export WESTLAKE_ANDROID_NATIVE_TARGETS=(.*)$', re.M)
    found = list(pattern.finditer(text))
    if len(found) != 1: raise ValueError('Expected exactly one native targets export')
    m = found[0]; values = shlex.split(m.group(1))
    if len(values) != 1 or not re.fullmatch(r'[A-Za-z0-9_.:+-]+', values[0]):
        raise ValueError('Targets must be a literal colon-separated library list')
    current = values[0].split(':')
    if any(not x for x in current): raise ValueError('Empty target entry')
    merged = list(dict.fromkeys(current+targets))
    text = text[:m.start(1)]+':'.join(merged)+text[m.end(1):]
    if 'stability46/prelaunch_map_count.sh' in text:
        if text.splitlines().count(CHECK) != 1: raise ValueError('Unknown/duplicate map_count hook')
    else:
        first, rest = text.split('\n', 1)
        text = first+'\n'+CHECK+'\n'+rest
    subprocess.run(['sh', '-n'], input=text.encode(), check=True)
    return text.encode()

def atomic_write(path, data, mode):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.stability46-', delete=False) as f:
        tmp = Path(f.name)
        try:
            f.write(data); f.flush(); os.fchmod(f.fileno(), mode); os.fsync(f.fileno())
            if path.exists():
                old = path.stat()
                # Preserve ownership on a privileged local staging operation.
                if os.geteuid() == 0: os.fchown(f.fileno(), old.st_uid, old.st_gid)
            os.replace(tmp, path)
        finally:
            if tmp.exists(): tmp.unlink()
    if digest(path.read_bytes()) != digest(data): raise RuntimeError('Write SHA mismatch: '+str(path))

def plan(stage, workspace, manifest):
    updates = {}
    for fix in manifest['binaries']:
        src = workspace/fix['source']; data = src.read_bytes()
        if digest(data) != fix['sha256']: raise ValueError('Source SHA mismatch: '+str(src))
        dest = confined(stage, fix['destination'])
        if not dest.is_file(): raise ValueError('Missing runtime file: '+str(dest))
        before = digest(dest.read_bytes())
        if before not in (fix['original_sha256'], fix['sha256']):
            raise ValueError('Unknown baseline; do not overwrite integrated fixes: '+str(dest)+' '+before)
        updates[fix['destination']] = (data, stat.S_IMODE(dest.stat().st_mode))
    run = confined(stage, 'run.sh')
    updates['run.sh'] = (rewrite_run(run.read_bytes(), manifest['targets']), stat.S_IMODE(run.stat().st_mode))
    for name in ('prelaunch_map_count.sh', 'run-with-fixes.sh'):
        data = (HERE/name).read_bytes()
        subprocess.run(['sh', '-n'], input=data, check=True)
        rel = 'stability46/'+name; dest = confined(stage, rel)
        if dest.exists() and dest.read_bytes() != data: raise ValueError('Unknown existing hook: '+str(dest))
        updates[rel] = (data, 0o755)
    sums = ''.join(digest(data)+'  '+rel+'\n' for rel,(data,_) in sorted(updates.items())).encode()
    confined(stage, 'stability46/SHA256SUMS')
    updates['stability46/SHA256SUMS'] = (sums, 0o644)
    return updates

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stage', type=Path, help='unpacked runtime root containing run.sh, not framework-only stage')
    ap.add_argument('--workspace', type=Path, default=Path.home()/'a2hlab/ws')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    if args.stage.is_symlink(): raise ValueError('Stage itself cannot be a symlink')
    stage = args.stage.resolve(strict=True)
    manifest = json.loads((HERE/'fixes.json').read_text())
    # Validate all inputs before creating even the lock/receipt directories.
    updates = plan(stage, args.workspace.resolve(), manifest)
    if args.dry_run:
        print(json.dumps({k: digest(v[0]) for k,v in updates.items()}, indent=2)); return
    state = confined(stage, '.stability46'); state.mkdir(exist_ok=True)
    lock = confined(stage, '.stability46/apply.lock')
    with lock.open('a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        updates = plan(stage, args.workspace.resolve(), manifest)
        receipt = confined(stage, '.stability46/receipt.json')
        prior = json.loads(receipt.read_text()) if receipt.exists() else None
        if prior and prior['recipe'] != manifest['recipe']: raise ValueError('Other recipe receipt present')
        original = dict(prior['originals']) if prior else {}
        for rel, (data, mode) in updates.items():
            dest = confined(stage, rel)
            if dest.exists() and dest.read_bytes() != data:
                old = dest.read_bytes(); sha = digest(old)
                backup = confined(stage, '.stability46/backups/'+sha)
                if backup.exists():
                    if digest(backup.read_bytes()) != sha: raise ValueError('Corrupt backup')
                else: atomic_write(backup, old, 0o600)
                original.setdefault(rel, sha)
            if not dest.exists() or dest.read_bytes() != data: atomic_write(dest, data, mode)
            if digest(dest.read_bytes()) != digest(data): raise RuntimeError('Final SHA mismatch: '+rel)
            print('VERIFIED', digest(data), rel)
        record = dict(recipe=manifest['recipe'], manifest_sha256=digest((HERE/'fixes.json').read_bytes()),
                      originals=original, installed={k:digest(v[0]) for k,v in updates.items()},
                      targets=manifest['targets'], device_validated=False)
        blob = (json.dumps(record, indent=2, sort_keys=True)+'\n').encode()
        if not receipt.exists() or receipt.read_bytes() != blob: atomic_write(receipt, blob, 0o644)
        print('RECEIPT', digest(blob), receipt)

if __name__ == '__main__': main()
