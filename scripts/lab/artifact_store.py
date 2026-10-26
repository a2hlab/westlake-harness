#!/usr/bin/env python3
"""Immutable content-addressed artifact store with clean restore (t1-store).

    artifact_store.py ingest  --manifest M --source-root R --store S
    artifact_store.py verify  --manifest M --store S
    artifact_store.py restore --manifest M --store S --dest D

All commands print one JSON object to stdout and exit 0 on success, nonzero on any rejection.

Manifest: schema westlake-artifact-release/v1; files[] items carry a safe relative path,
lowercase 64-hex sha256, non-negative size, integer mode, and a role; release_id is a safe
identifier. Other metadata is preserved verbatim.

Store layout: objects/sha256/<first2>/<fullhash>; releases/<release_id>.json is published
atomically, never overwritten, only after every object hash passes; re-ingesting identical
bytes is allowed, divergent content under the same id is rejected.
"""
import ctypes
import ctypes.util
import hashlib
import json
import os
import shutil
import sys
import tempfile

SCHEMA = 'westlake-artifact-release/v1'
READ_CHUNK = 1 << 20


def rename_no_replace(src, dst):
    """Atomic rename that fails if dst exists. macOS renamex_np(RENAME_EXCL) or
    Linux renameat2(RENAME_NOREPLACE); unknown platforms refuse."""
    if os.path.lexists(dst):
        raise Reject(f'restore destination already exists: {dst}')
    if sys.platform == 'darwin':
        libc = ctypes.CDLL(None)
        RENAME_EXCL = 0x4
        rc = libc.renamex_np(os.fsencode(src), os.fsencode(dst), RENAME_EXCL)
        if rc != 0:
            raise Reject(f'renamex_np failed rc={rc} for {dst}')
        return
    if sys.platform.startswith('linux'):
        libc = ctypes.CDLL(None)
        try:
            fn = libc.renameat2
        except AttributeError:
            raise Reject('renameat2 unavailable on this platform')
        RENAME_NOREPLACE = 1
        AT_FDCWD = -100
        rc = fn(AT_FDCWD, os.fsencode(src), AT_FDCWD, os.fsencode(dst), RENAME_NOREPLACE)
        if rc != 0:
            raise Reject(f'renameat2 failed for {dst}')
        return
    raise Reject(f'no-replace rename unsupported on platform {sys.platform}')


class Reject(Exception):
    pass


def _safe_component(s, what):
    if not isinstance(s, str) or not s or s in ('.', '..') or '/' in s or '\\' in s:
        raise Reject(f'unsafe {what}: {s!r}')
    return s


def safe_relpath(p):
    """Reject absolute paths, traversal, empty segments, NUL."""
    if not isinstance(p, str) or not p or '\x00' in p or '\\' in p:
        raise Reject(f'unsafe path: {p!r}')
    if p.startswith('/') or (len(p) > 1 and p[1] == ':'):
        raise Reject(f'absolute path rejected: {p!r}')
    parts = p.split('/')
    for part in parts:
        if part in ('', '.', '..'):
            raise Reject(f'unsafe path component in {p!r}')
    return parts


def safe_release_id(rid):
    import re as _re
    if not isinstance(rid, str) or not _re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', rid):
        raise Reject(f'unsafe release_id: {rid!r}')
    return rid


def validate_manifest(doc):
    if not isinstance(doc, dict):
        raise Reject('manifest is not an object')
    if doc.get('schema') != SCHEMA:
        raise Reject(f"schema must be {SCHEMA}")
    rid = safe_release_id(doc.get('release_id'))
    files = doc.get('files')
    if not isinstance(files, list):
        raise Reject('files must be a list')
    seen = {}
    out = []
    for i, f in enumerate(files):
        if not isinstance(f, dict):
            raise Reject(f'files[{i}] not an object')
        parts = safe_relpath(f.get('path'))
        sha = f.get('sha256')
        if not (isinstance(sha, str) and len(sha) == 64 and sha == sha.lower()
                and all(c in '0123456789abcdef' for c in sha)):
            raise Reject(f'files[{i}] sha256 must be lowercase 64-hex')
        size = f.get('size')
        if not (isinstance(size, int) and not isinstance(size, bool) and size >= 0):
            raise Reject(f'files[{i}] size must be a non-negative integer')
        mode = f.get('mode')
        if not (isinstance(mode, int) and not isinstance(mode, bool) and 0 <= mode <= 0o777):
            raise Reject(f'files[{i}] mode must be an integer permission <=0o777')
        role = f.get('role')
        if not isinstance(role, str) or not role:
            raise Reject(f'files[{i}] role required')
        norm = '/'.join(parts)
        if norm in seen:
            raise Reject(f'duplicate path: {norm!r}')
        seen[norm] = True
        out.append({'path': norm, 'sha256': sha, 'size': size, 'mode': mode, 'role': role})
    for name in seen:
        parts = name.split('/')
        for i in range(1, len(parts)):
            parent = '/'.join(parts[:i])
            if parent in seen:
                raise Reject(f'parent/child path conflict: {parent!r} vs {name!r}')
    return {'release_id': rid, 'files': out, 'doc': doc}


def load_manifest(path):
    try:
        doc = json.loads(open(path, encoding='utf-8').read())
    except (OSError, json.JSONDecodeError) as e:
        raise Reject(f'manifest unreadable: {e}')
    return validate_manifest(doc)


def object_path(store, sha):
    return os.path.join(store, 'objects', 'sha256', sha[:2], sha)


def publish_atomic(path, source_path, expect_sha=None, expect_size=None):
    """Stream source_path bytes into a NEW temporary inode in the destination directory,
    hash the copied bytes (TOCTOU guard), fsync, then publish with an atomic no-clobber
    link. The source file is never hardlinked or otherwise mutated."""
    if os.path.lexists(path):
        raise Reject(f'publish target exists: {path}')
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix='.publish-')
    try:
        h = hashlib.sha256()
        total = 0
        with os.fdopen(fd, 'wb') as out, open(source_path, 'rb') as f:
            while True:
                chunk = f.read(READ_CHUNK)
                if not chunk:
                    break
                out.write(chunk)
                h.update(chunk)
                total += len(chunk)
            out.flush()
            os.fsync(out.fileno())
        if expect_sha is not None and h.hexdigest() != expect_sha:
            raise Reject(f'temp copy hash drift for {path}: source changed during read')
        if expect_size is not None and total != expect_size:
            raise Reject(f'temp copy size drift for {path}')
        try:
            os.link(tmp, path)
        except FileExistsError:
            raise Reject(f'publish target exists: {path}')
    finally:
        os.unlink(tmp)


def stream_hash(path):
    h = hashlib.sha256()
    total = 0
    with open(path, 'rb') as f:
        while True:
            chunk = f.read(READ_CHUNK)
            if not chunk:
                break
            h.update(chunk)
            total += len(chunk)
    return h.hexdigest(), total


def verify_object(store, item):
    op = object_path(store, item['sha256'])
    reject_symlink_ancestors(op)
    if not os.path.isfile(op):
        raise Reject(f"missing object {item['sha256']} for {item['path']}")
    if os.path.islink(op):
        raise Reject(f'object is a symlink: {op}')
    sha, size = stream_hash(op)
    if size != item['size']:
        raise Reject(f"size mismatch for {item['path']}: store {size} != manifest {item['size']}")
    if sha != item['sha256']:
        raise Reject(f"corrupt object for {item['path']}: {sha[:12]} != {item['sha256'][:12]}")


def reject_symlink_ancestors(path, stop_at=None):
    """Reject if any ancestor component of path (up to stop_at or filesystem root) is a symlink."""
    cur = os.path.abspath(path)
    while True:
        parent = os.path.dirname(cur)
        if cur == parent or (stop_at and cur == os.path.abspath(stop_at)):
            break
        if os.path.islink(cur):
            raise Reject(f'symlink ancestor rejected: {cur}')
        cur = parent


def cmd_ingest(args):
    man = load_manifest(args['--manifest'])
    rid = man['release_id']
    store = args['--store']
    reject_symlink_ancestors(store)
    reject_symlink_ancestors(args['--source-root'])
    sroot = os.path.realpath(args['--source-root'])
    rel_path = os.path.join(store, 'releases', rid + '.json')
    reject_symlink_ancestors(rel_path)
    if os.path.lexists(rel_path):
        existing = json.loads(open(rel_path, encoding='utf-8').read())
        if existing != man['doc']:
            raise Reject(f'release {rid!r} already published with different content')
        for item in man['files']:
            verify_object(store, item)
        return {'status': 'idempotent', 'release_id': rid, 'objects': 0}
    objects = 0
    staged = {}
    try:
        for item in man['files']:
            src = os.path.join(sroot, *item['path'].split('/'))
            if os.path.islink(src):
                raise Reject(f'symlink rejected: {src}')
            rel_parts = item['path'].split('/')
            cur = sroot
            for part in rel_parts[:-1]:
                cur = os.path.join(cur, part)
                if os.path.islink(cur):
                    raise Reject(f'symlink ancestor rejected: {cur}')
            real = os.path.realpath(src)
            if not (real == sroot or real.startswith(sroot + os.sep)):
                raise Reject(f'path escapes source-root: {src}')
            if not os.path.isfile(src):
                raise Reject(f'not a regular file: {src}')
            sha, size = stream_hash(src)
            if size != item['size']:
                raise Reject(f"size mismatch for {item['path']}: source {size} != manifest {item['size']}")
            if sha != item['sha256']:
                raise Reject(f"hash mismatch for {item['path']}: source does not match manifest")
            if sha in staged and staged[sha][1] != item['size']:
                raise Reject(f'same sha256 with conflicting sizes in manifest: {sha[:12]}')
            op = object_path(store, sha)
            if os.path.lexists(op):
                if os.path.islink(op):
                    raise Reject(f'existing object is a symlink: {op}')
                existing_sha, existing_size = stream_hash(op)
                if existing_sha != sha:
                    raise Reject(f'existing corrupt object at {op}')
                if existing_size != item['size']:
                    raise Reject(f'existing object size drift at {op}')
                continue
            if sha in staged:
                continue
            reject_symlink_ancestors(op, stop_at=store)
            os.makedirs(os.path.dirname(op), exist_ok=True)
            staged[sha] = (src, item['size'])
            objects += 1
        for sha, (src, size) in staged.items():
            op = object_path(store, sha)
            publish_atomic(op, src, expect_sha=sha, expect_size=size)
            os.chmod(op, 0o444)
        reject_symlink_ancestors(rel_path, stop_at=store)
        os.makedirs(os.path.dirname(rel_path), exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(rel_path), prefix='.release-')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(man['doc'], f, indent=1)
        try:
            os.link(tmp, rel_path)
        except FileExistsError:
            os.unlink(tmp)
            existing = json.loads(open(rel_path, encoding='utf-8').read())
            if existing != man['doc']:
                raise Reject(f'release {rid!r} concurrently published with different content')
            return {'status': 'idempotent', 'release_id': rid, 'objects': objects}
        os.unlink(tmp)
        return {'status': 'published', 'release_id': rid, 'objects': objects}
    except Reject:
        raise


def cmd_verify(args):
    man = load_manifest(args['--manifest'])
    store = args['--store']
    for item in man['files']:
        verify_object(store, item)
    return {'status': 'verified', 'release_id': man['release_id'], 'objects': len(man['files'])}


def cmd_restore(args):
    man = load_manifest(args['--manifest'])
    store = args['--store']
    dest = args['--dest']
    reject_symlink_ancestors(store)
    if os.path.lexists(dest):
        raise Reject(f'dest must not exist: {dest}')
    if os.path.islink(dest):
        raise Reject(f'dest is a symlink: {dest}')
    reject_symlink_ancestors(os.path.dirname(os.path.abspath(dest)))
    for item in man['files']:
        verify_object(store, item)
    parent = os.path.dirname(os.path.abspath(dest))
    os.makedirs(parent, exist_ok=True)
    tmp = tempfile.mkdtemp(dir=parent, prefix='.restore-')
    try:
        for item in man['files']:
            op = object_path(store, item['sha256'])
            target = os.path.join(tmp, *item['path'].split('/'))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            h = hashlib.sha256()
            total = 0
            with open(op, 'rb') as s, open(target, 'wb') as d:
                while True:
                    chunk = s.read(READ_CHUNK)
                    if not chunk:
                        break
                    d.write(chunk)
                    h.update(chunk)
                    total += len(chunk)
                d.flush()
                os.fsync(d.fileno())
            if h.hexdigest() != item['sha256'] or total != item['size']:
                raise Reject(f"restored copy drift for {item['path']}")
            os.chmod(target, item['mode'])
        os.link if False else None
        rename_no_replace(tmp, dest)
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
    return {'status': 'restored', 'release_id': man['release_id'], 'files': len(man['files']), 'dest': dest}


COMMANDS = {'ingest': cmd_ingest, 'verify': cmd_verify, 'restore': cmd_restore}


def main(argv):
    if len(argv) < 2 or argv[1] not in COMMANDS:
        print('usage: artifact_store.py {ingest|verify|restore} --manifest M --source-root R --store S [--dest D]', file=sys.stderr)
        return 2
    cmd = argv[1]
    args = {}
    it = iter(argv[2:])
    for tok in it:
        if tok.startswith('--'):
            args[tok] = next(it)
    for req in ('--manifest', '--store'):
        if req not in args:
            print(json.dumps({'status': 'error', 'error': f'missing {req}'}))
            return 2
    if cmd == 'ingest' and '--source-root' not in args:
        print(json.dumps({'status': 'error', 'error': 'missing --source-root'}))
        return 2
    if cmd == 'restore' and '--dest' not in args:
        print(json.dumps({'status': 'error', 'error': 'missing --dest'}))
        return 2
    try:
        out = COMMANDS[cmd](args)
    except Reject as e:
        print(json.dumps({'status': 'rejected', 'error': str(e)}))
        return 1
    except OSError as e:
        print(json.dumps({'status': 'error', 'error': str(e)}))
        return 1
    print(json.dumps(out))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
