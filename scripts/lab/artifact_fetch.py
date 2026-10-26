#!/usr/bin/env python3
"""Fetch a pinned release from an SSH artifact store into a new, verified directory.

No local-source/cache fallback. Requires Python 3 and rsync with --protect-args.
Remote is an SSH config alias; authentication stays outside the public manifest.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def safe_new(path):
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        if part.is_symlink():
            raise ValueError('symlink path: ' + str(part))
    if path.exists():
        raise ValueError('path already exists: ' + str(path))
    if not path.parent.is_dir():
        raise ValueError('parent directory must exist: ' + str(path.parent))
    return path


def transport_source(remote, root):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', remote or ''):
        raise ValueError('remote must be an SSH config alias')
    if not root or not re.fullmatch(r'/?[A-Za-z0-9_][A-Za-z0-9_./-]*', root):
        raise ValueError('remote-store must be a plain path without shell syntax')
    if any(p in ('.', '..', '') for p in root.lstrip('/').rstrip('/').split('/')):
        raise ValueError('invalid remote-store component')
    return remote + ':' + root.rstrip('/') + '/'


def object_paths(manifest):
    if not isinstance(manifest, dict) or manifest.get('schema') != 'westlake-artifact-release/v1':
        raise ValueError('unsupported manifest schema')
    rows = manifest.get('files')
    if not isinstance(rows, list) or not rows:
        raise ValueError('manifest must contain files')
    result = set()
    for row in rows:
        sha = row.get('sha256') if isinstance(row, dict) else None
        if not isinstance(sha, str) or not re.fullmatch('[0-9a-f]{64}', sha):
            raise ValueError('invalid object SHA256')
        result.add('objects/sha256/' + sha[:2] + '/' + sha)
    return sorted(result)


def execute(argv, report, timeout=3600):
    row = {'argv': argv, 'start_utc': utc()}
    report['commands'].append(row)
    started = time.monotonic()
    try:
        result = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        row.update(rc=result.returncode, stdout=result.stdout, stderr=result.stderr)
    except subprocess.TimeoutExpired as exc:
        def text(value):
            return value.decode(errors='replace') if isinstance(value, bytes) else (value or '')
        row.update(rc=None, timed_out=True, stdout=text(exc.stdout), stderr=text(exc.stderr))
        raise RuntimeError('command timed out') from exc
    finally:
        row.update(end_utc=utc(), elapsed_seconds=time.monotonic() - started)
    if result.returncode:
        raise RuntimeError('command failed: ' + Path(argv[0]).name)
    return result


def fetch(args):
    # Reserve a distinct receipt only after all destination preconditions pass.
    source = transport_source(args.remote, args.remote_store)
    cache, dest, receipt = [safe_new(v) for v in (args.cache, args.dest, args.receipt)]
    paths = (cache, dest, receipt)
    if len(set(paths)) != 3 or any(a in b.parents for a in paths for b in paths if a != b):
        raise ValueError('cache, dest and receipt must be disjoint')
    original = Path(args.manifest).read_bytes()
    digest = hashlib.sha256(original).hexdigest()
    if args.manifest_sha256 and digest != args.manifest_sha256:
        raise ValueError('manifest SHA256 mismatch')
    manifest = json.loads(original)
    members = object_paths(manifest)
    report = {'schema': 'westlake-artifact-fetch-receipt/v1', 'started_utc': utc(),
              'manifest_sha256': digest, 'object_count': len(members),
              'remote': args.remote, 'remote_store': args.remote_store,
              'cache': str(cache), 'dest': str(dest), 'local_fallback': False,
              'commands': [], 'success': False}
    with receipt.open('x') as output:
        try:
            cache.mkdir()
            pinned = cache / 'requested-manifest.json'
            pinned.write_bytes(original)
            files = cache / 'requested-objects.txt'
            files.write_text('\n'.join(members) + '\n')
            execute(['rsync', '-rt', '--protect-args', '--checksum',
                     '--files-from=' + str(files), '-e',
                     'ssh -o BatchMode=yes -o ConnectTimeout=15',
                     source, str(cache) + '/'], report)
            tool = str(Path(__file__).with_name('artifact_store.py'))
            base = [sys.executable, tool]
            execute(base + ['verify', '--manifest', str(pinned), '--store', str(cache)], report)
            execute(base + ['restore', '--manifest', str(pinned), '--store', str(cache),
                            '--dest', str(dest)], report)
            report['success'] = True
        except (OSError, ValueError, RuntimeError) as exc:
            report['error'] = str(exc)
        finally:
            report['finished_utc'] = utc()
            json.dump(report, output, ensure_ascii=False, indent=2)
            output.write('\n')
            output.flush()
            os.fsync(output.fileno())
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--manifest-sha256')
    ap.add_argument('--remote', default=os.environ.get('WESTLAKE_ARTIFACT_REMOTE'))
    ap.add_argument('--remote-store', default=os.environ.get('WESTLAKE_ARTIFACT_REMOTE_STORE'))
    ap.add_argument('--cache', required=True)
    ap.add_argument('--dest', required=True)
    ap.add_argument('--receipt', required=True)
    args = ap.parse_args(argv)
    try:
        report = fetch(args)
    except (OSError, ValueError, TypeError) as exc:
        report = {'success': False, 'error': str(exc)}
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['success'] else 1


if __name__ == '__main__':
    sys.exit(main())
