#!/bin/bash
# Existing local container, docker cp only. Never mounts or copies the SDK.
set -euo pipefail
exec python3 - "$@" <<'PY'
import io, json, os, pathlib, shutil, subprocess, sys, tarfile, tempfile

def refuse(reason):
    raise SystemExit('COPY_RUNNER_REFUSE ' + reason)
if len(sys.argv) != 4 or sys.argv[1:3] != ['run', '--']:
    refuse('usage: copy_dockbuild.sh run -- CMD')
container = os.environ.get('R10_CONTAINER', '')
if not container or container.startswith('-'):
    refuse('R10_CONTAINER required')
paths = {}
for key in ('SOURCE_REPO', 'OH_NATIVE', 'OUT'):
    value = os.environ.get(key, '')
    p = pathlib.Path(value)
    if not p.is_absolute() or '\n' in value or not p.is_dir():
        refuse(key + ' must be an existing absolute directory')
    paths[key] = p
out = paths['OUT']
if out == pathlib.Path('/') or out.resolve().is_relative_to(pathlib.Path('/private/tmp')) or out.resolve().is_relative_to(pathlib.Path('/tmp')):
    refuse('OUT must be persistent')
if paths['OH_NATIVE'] == out or paths['OH_NATIVE'] in out.parents or out in paths['OH_NATIVE'].parents:
    refuse('OUT and OH_NATIVE must be disjoint')

def run(args, **kwargs):
    return subprocess.run(['docker', *args], check=True, **kwargs)
info = json.loads(run(['inspect', container], stdout=subprocess.PIPE).stdout)
if len(info) != 1:
    refuse('container inspect count')
info = info[0]
if info.get('Image') != 'sha256:12ffb9324ca4df6427cbf6a6da0ac8ce575599291e933724275fce704520db63':
    refuse('container image drift')
if not info.get('State', {}).get('Running') or info.get('Mounts'):
    refuse('requires running container with zero mounts')
# Pin the inspected container ID, not a name that might be reassigned.
cid = info['Id']
run(['exec', '--user', '0', cid, 'mkdir', '-p', str(out), str(out / 'raw')])
# Send OUT without host raw logs (which are currently open). SOURCE_REPO checks
# run on the host; all compiler inputs were already copied into OUT by recipe.
with tempfile.TemporaryFile() as stream:
    with tarfile.open(fileobj=stream, mode='w') as archive:
        def checked(member):
            if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                refuse('OUT contains a link or special file')
            return member
        for p in sorted(out.iterdir()):
            if p.name != 'raw':
                archive.add(p, arcname=p.name, filter=checked)
    stream.seek(0)
    run(['cp', '-', cid + ':' + str(out)], stdin=stream, stdout=sys.stderr)
run(['exec', '--user', '0', cid, 'chown', '-R', '501:501', str(out)])
# SDK is pre-provisioned by outer. This runner never chmod/chown/copies it.
# Non-root execution leaves the root-owned SDK untouched; tools stage checks pins.
result = subprocess.run(['docker', 'exec', '--user', '501:501', '--workdir', str(out),
                         cid, 'bash', '-lc', sys.argv[3]])
# Recover generated products even on command failure. Never reverse-copy raw/.
# The only container-created raw file is the linker's why-extract receipt.
try:
    with tempfile.TemporaryDirectory(prefix='r10-copy-return-') as tmp:
        for name in ('link-only.NOT-FOR-DEPLOY', 'unstripped', 'artifacts'):
            dst = pathlib.Path(tmp) / name
            dst.mkdir()
            run(['cp', cid + ':' + str(out / name) + '/.', str(dst)], stdout=sys.stderr)
            for p in dst.rglob('*'):
                if p.is_symlink() or not (p.is_file() or p.is_dir()):
                    refuse('returned product is not a regular file/directory')
            shutil.copytree(dst, out / name, dirs_exist_ok=True)
        receipt = out / 'raw/20-archive-extraction.txt'
        probe = subprocess.run(['docker', 'exec', cid, 'test', '-f', str(receipt)])
        if probe.returncode == 0:
            dst = pathlib.Path(tmp) / '20-archive-extraction.txt'
            run(['cp', cid + ':' + str(receipt), str(dst)], stdout=sys.stderr)
            if dst.is_symlink() or not dst.is_file():
                refuse('linker receipt is not regular')
            shutil.copyfile(dst, receipt)
        elif probe.returncode != 1:
            refuse('linker receipt probe failed')
except (subprocess.CalledProcessError, OSError) as exc:
    print('COPY_RUNNER_RETURN_FAILED: ' + str(exc), file=sys.stderr)
    sys.exit(result.returncode or 2)
sys.exit(result.returncode)
PY
