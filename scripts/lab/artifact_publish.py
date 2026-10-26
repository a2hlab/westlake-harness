#!/usr/bin/env python3
"""Publish verified CAS objects through a private SSH staging directory, manifest last."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
import tempfile
import uuid

import artifact_fetch as fetch


def check_regular(path):
    for part in [path, *path.parents]:
        if part.is_symlink():
            raise ValueError('symlink rejected: ' + str(part))


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def server_publish(args):
    # No shell input is interpreted here. All files arrived in a unique quarantine.
    import artifact_store
    incoming, store = Path(args.incoming).absolute(), Path(args.store).absolute()
    check_regular(incoming); check_regular(store)
    manifest = incoming / 'manifest.json'
    doc = json.loads(manifest.read_text())
    artifact_store.validate_manifest(doc)
    # Validate via the public CLI as well; do not depend on its internal return type.
    report = {'commands': []}
    fetch.execute([sys.executable, str(Path(__file__).with_name('artifact_store.py')),
                   'verify', '--manifest', str(manifest), '--store', str(incoming)], report)
    release = store / 'releases' / (doc['release_id'] + '.json')
    check_regular(release)
    if release.exists() and release.read_bytes() != manifest.read_bytes():
        raise ValueError('release ID already published with different manifest bytes')
    for row in doc['files']:
        rel = Path('objects/sha256') / row['sha256'][:2] / row['sha256']
        src, dst = incoming / rel, store / rel
        check_regular(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)
        # A hardlink from verified private upload staging is safe: it is not a source worktree.
        try:
            os.link(src, dst)
        except FileExistsError:
            pass
        if dst.stat().st_size != row['size'] or digest(dst) != row['sha256']:
            raise ValueError('remote object conflict/corruption: ' + row['sha256'])
        os.chmod(dst, 0o444)
    # Full final-store verification precedes the release name becoming visible.
    fetch.execute([sys.executable, str(Path(__file__).with_name('artifact_store.py')),
                   'verify', '--manifest', str(manifest), '--store', str(store)], report)
    release.parent.mkdir(parents=True, exist_ok=True)
    if not release.exists():
        with tempfile.NamedTemporaryFile(dir=release.parent, delete=False) as out:
            tmp = Path(out.name)
            out.write(manifest.read_bytes()); out.flush(); os.fsync(out.fileno())
        try:
            os.chmod(tmp, 0o444)
            try: os.link(tmp, release)
            except FileExistsError:
                if release.read_bytes() != manifest.read_bytes():
                    raise ValueError('concurrent release conflict')
        finally:
            tmp.unlink()
    return {'success': True, 'release_id': doc['release_id'],
            'manifest_sha256': digest(release), 'files': len(doc['files']),
            'objects': len(fetch.object_paths(doc)), 'verification': report}


def publish(args):
    fetch.transport_source(args.remote, args.remote_store)
    receipt = fetch.safe_new(args.receipt)
    manifest = Path(args.manifest).resolve()
    doc = json.loads(manifest.read_text())
    paths = fetch.object_paths(doc)
    store = Path(args.store).resolve()
    report = {'schema': 'westlake-artifact-publish-receipt/v1', 'success': False,
              'manifest_sha256': digest(manifest), 'commands': [], 'started_utc': fetch.utc()}
    ssh = ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=15', args.remote]
    incoming = args.remote_store.rstrip('/') + '/.incoming/' + uuid.uuid4().hex
    with receipt.open('x') as output:
        try:
            tool = Path(__file__).with_name('artifact_store.py')
            fetch.execute([sys.executable, str(tool), 'verify', '--manifest', str(manifest),
                           '--store', str(store)], report)
            prepare = ('import pathlib,sys,os; p=pathlib.Path(sys.argv[1]).absolute(); '
                       'assert not any(x.is_symlink() for x in [p,*p.parents]); '
                       'p.mkdir(parents=True,exist_ok=True,mode=0o700); os.chmod(p,0o700); '
                       'pathlib.Path(sys.argv[2]).mkdir(parents=True,exist_ok=False,mode=0o700)')
            fetch.execute(ssh + [shlex.join(['python3', '-c', prepare,
                                           args.remote_store, incoming])], report)
            with tempfile.TemporaryDirectory(prefix='artifact-publish-') as scratch:
                stage = Path(scratch)
                (stage/'objects.txt').write_text('\n'.join(paths) + '\n')
                shutil.copyfile(manifest, stage/'manifest.json')
                for name in ('artifact_store.py', 'artifact_fetch.py', 'artifact_publish.py'):
                    shutil.copyfile(Path(__file__).with_name(name), stage/name)
                base = ['rsync', '-rt', '--protect-args', '--checksum', '-e',
                        'ssh -o BatchMode=yes -o ConnectTimeout=15']
                remote_incoming = args.remote + ':' + incoming + '/'
                fetch.execute(base + ['--files-from='+str(stage/'objects.txt'),
                                      str(store)+'/', remote_incoming], report)
                fetch.execute(base + [str(stage)+'/', remote_incoming], report)
            command = ['python3', incoming+'/artifact_publish.py', '--server-publish',
                       '--incoming', incoming, '--store', args.remote_store]
            result = fetch.execute(ssh + [shlex.join(command)], report)
            report['server'] = json.loads(result.stdout)
            report['success'] = report['server']['success']
            report['remote_incoming'] = incoming
        except (OSError, ValueError, RuntimeError) as exc:
            report['error'] = str(exc)
        finally:
            report['finished_utc'] = fetch.utc()
            json.dump(report, output, indent=2); output.write('\n')
            output.flush(); os.fsync(output.fileno())
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--server-publish', action='store_true')
    parser.add_argument('--incoming')
    parser.add_argument('--store', required=True)
    parser.add_argument('--manifest')
    parser.add_argument('--receipt')
    parser.add_argument('--remote', default=os.environ.get('WESTLAKE_ARTIFACT_REMOTE'))
    parser.add_argument('--remote-store', default=os.environ.get('WESTLAKE_ARTIFACT_REMOTE_STORE'))
    args = parser.parse_args()
    try:
        result = server_publish(args) if args.server_publish else publish(args)
    except (OSError, ValueError, TypeError) as exc:
        result = {'success': False, 'error': str(exc)}
    print(json.dumps(result))
    return 0 if result['success'] else 1


if __name__ == '__main__':
    sys.exit(main())
