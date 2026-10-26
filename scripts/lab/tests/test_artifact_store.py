#!/usr/bin/env python3
"""Real CLI subprocess tests for scripts/lab/artifact_store.py (artifact_store_contract).

Covers the t1-store acceptance scenarios: restore without the original tree, corruption and
missing-object rejection, path/overwrite rejection, and immutable/interrupted publication.
No network, no device, no external packages.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

P = Path(__file__).resolve().parent
TOOL = P.parent / 'artifact_store.py'
checks = []


def run(*argv):
    r = subprocess.run([sys.executable, str(TOOL), *argv], capture_output=True, text=True, timeout=60)
    out = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {}
    return r.returncode, out


def sha(b):
    return hashlib.sha256(b).hexdigest()


def write(path, data, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    os.chmod(path, mode)


def make_manifest(tmp, root, files, rid='r1', schema='westlake-artifact-release/v1'):
    items = []
    for rel, data, mode in files:
        items.append({'path': rel, 'sha256': sha(data), 'size': len(data), 'mode': mode, 'role': 'binary'})
    doc = {'schema': schema, 'release_id': rid, 'build_status': 'kept', 'files': items}
    mp = tmp / 'manifest.json'
    mp.write_text(json.dumps(doc))
    return mp, doc


def case(name, fn):
    fn()
    checks.append(name)


def main():
    with tempfile.TemporaryDirectory(prefix='artifact-store-test-') as d:
        tmp = Path(d).resolve()  # /var is a symlink to /private/var on macOS; strict ancestor checks need the real path

        # Scenario 1: restore without the original worktree; modes/hashes match; store untouched by edits.
        def s1():
            src = tmp / 's1src'
            data_a, data_b = b'alpha' * 500, b'\x00' * (2 << 20)  # >1MB exercises streaming
            write(src / 'a.bin', data_a, 0o640)
            write(src / 'sub' / 'b.bin', data_b, 0o600)
            mp, _ = make_manifest(tmp, src, [('a.bin', data_a, 0o640), ('sub/b.bin', data_b, 0o600)])
            store = tmp / 's1store'
            rc, out = run('ingest', '--manifest', str(mp), '--source-root', str(src), '--store', str(store))
            assert rc == 0 and out['status'] == 'published' and out['objects'] == 2, out
            src.rename(tmp / 's1src-gone')  # source disappears
            rc, out = run('verify', '--manifest', str(mp), '--store', str(store))
            assert rc == 0 and out['status'] == 'verified', out
            dest = tmp / 's1out'
            rc, out = run('restore', '--manifest', str(mp), '--store', str(store), '--dest', str(dest))
            assert rc == 0 and out['status'] == 'restored', out
            assert (dest / 'a.bin').read_bytes() == data_a
            assert (dest / 'sub' / 'b.bin').read_bytes() == data_b
            assert (os.stat(dest / 'a.bin').st_mode & 0o7777) == 0o640
            assert (os.stat(dest / 'sub' / 'b.bin').st_mode & 0o7777) == 0o600
            # Editing restored files must not change store objects.
            (dest / 'a.bin').write_bytes(b'tampered')
            rc, out = run('verify', '--manifest', str(mp), '--store', str(store))
            assert rc == 0, out
            # Restored file is a copy, not a hardlink to the object.
            ia, io = os.stat(dest / 'a.bin').st_ino, os.stat(store / 'objects' / 'sha256' / sha(data_a)[:2] / sha(data_a)).st_ino
            assert ia != io
        case('restore_without_original_tree_and_store_immutable', s1)

        # Scenario 2: corruption / missing / wrong-size all rejected; dest never created.
        def s2():
            src = tmp / 's2src'
            write(src / 'x.bin', b'xdata', 0o644)
            mp, _ = make_manifest(tmp, src, [('x.bin', b'xdata', 0o644)])
            store = tmp / 's2store'
            rc, out = run('ingest', '--manifest', str(mp), '--store', str(store), '--source-root', str(src))
            assert rc == 0
            op = store / 'objects' / 'sha256' / sha(b'xdata')[:2] / sha(b'xdata')
            dest = tmp / 's2out'
            # corrupt
            orig = op.read_bytes()
            os.chmod(op, 0o644)
            op.write_bytes(b'corrupt!')
            rc, out = run('verify', '--manifest', str(mp), '--store', str(store))
            assert rc != 0 and out['status'] == 'rejected', out
            rc, out = run('restore', '--manifest', str(mp), '--store', str(store), '--dest', str(dest))
            assert rc != 0 and not dest.exists(), out
            op.write_bytes(orig)
            os.chmod(op, 0o444)
            # missing
            op.unlink()
            rc, out = run('verify', '--manifest', str(mp), '--store', str(store))
            assert rc != 0
            rc, out = run('restore', '--manifest', str(mp), '--store', str(store), '--dest', str(dest))
            assert rc != 0 and not dest.exists(), out
            # wrong size in manifest vs store (rewrite manifest sha=store, size wrong)
            doc = json.loads(mp.read_text())
            doc['release_id'] = 'r1s'; doc['files'][0]['size'] = 99
            mp2 = tmp / 's2b.json'
            mp2.write_text(json.dumps(doc))
            write(store / 'objects' / 'sha256' / sha(b'xdata')[:2] / sha(b'xdata'), orig)
            os.chmod(store / 'objects' / 'sha256' / sha(b'xdata')[:2] / sha(b'xdata'), 0o444)
            rc, out = run('verify', '--manifest', str(mp2), '--store', str(store))
            assert rc != 0
        case('corruption_missing_size_rejected_dest_absent', s2)

        # Scenario 3: path & overwrite rejection.
        def s3():
            src = tmp / 's3src'
            write(src / 'ok.bin', b'ok', 0o644)
            store = tmp / 's3store'
            rc, out = run('ingest', '--manifest', str(make_manifest(tmp, src, [('ok.bin', b'ok', 0o644)])[0]),
                          '--source-root', str(src), '--store', str(store))
            assert rc == 0
            # traversal in manifest
            bad = tmp / 'bad-traverse.json'
            bad.write_text(json.dumps({'schema': 'westlake-artifact-release/v1', 'release_id': 'bad1',
                                       'files': [{'path': '../evil', 'sha256': sha(b'ok'), 'size': 2, 'mode': 420, 'role': 'x'}]}))
            rc, out = run('ingest', '--manifest', str(bad), '--source-root', str(src), '--store', str(store))
            assert rc != 0 and 'rejected' == out.get('status'), out
            # duplicate path
            dup = tmp / 'bad-dup.json'
            dup.write_text(json.dumps({'schema': 'westlake-artifact-release/v1', 'release_id': 'bad2',
                                       'files': [{'path': 'a', 'sha256': sha(b'ok'), 'size': 2, 'mode': 420, 'role': 'x'},
                                                 {'path': 'a', 'sha256': sha(b'ok'), 'size': 2, 'mode': 420, 'role': 'x'}]}))
            rc, out = run('ingest', '--manifest', str(dup), '--source-root', str(src), '--store', str(store))
            assert rc != 0
            # symlink source
            (src / 'link.bin').symlink_to(src / 'ok.bin')
            sl = tmp / 'bad-link.json'
            sl.write_text(json.dumps({'schema': 'westlake-artifact-release/v1', 'release_id': 'bad3',
                                      'files': [{'path': 'link.bin', 'sha256': sha(b'ok'), 'size': 2, 'mode': 420, 'role': 'x'}]}))
            rc, out = run('ingest', '--manifest', str(sl), '--source-root', str(src), '--store', str(store))
            assert rc != 0
            # dest already exists
            dest = tmp / 's3out'
            dest.mkdir()
            mp, _ = make_manifest(tmp, src, [('ok.bin', b'ok', 0o644)])
            rc, out = run('restore', '--manifest', str(mp), '--store', str(store), '--dest', str(dest))
            assert rc != 0 and (dest / 'ok.bin').exists() is False, out
            # same release id, different manifest -> rejected; published release bytes unchanged
            doc = json.loads(mp.read_text())
            doc['build_status'] = 'changed'
            mp2 = tmp / 's3b.json'
            mp2.write_text(json.dumps(doc))
            before = (store / 'releases' / 'r1.json').read_bytes()
            rc, out = run('ingest', '--manifest', str(mp2), '--source-root', str(src), '--store', str(store))
            assert rc != 0, out
            assert (store / 'releases' / 'r1.json').read_bytes() == before
        case('path_traversal_symlink_duplicate_existing_dest_rejected', s3)

        # Scenario 4: immutable + interrupted publication.
        def s4():
            src = tmp / 's4src'
            write(src / 'm.bin', b'm', 0o644)
            store = tmp / 's4store'
            mp, _ = make_manifest(tmp, src, [('m.bin', b'm', 0o644)])
            # interrupted: source fails hash check -> nothing published
            mpbad = tmp / 's4bad.json'
            doc = json.loads(mp.read_text())
            doc['files'][0]['sha256'] = sha(b'other')
            mpbad.write_text(json.dumps(doc))
            rc, out = run('ingest', '--manifest', str(mpbad), '--source-root', str(src), '--store', str(store))
            assert rc != 0
            assert not (store / 'releases' / 'r1.json').exists()
            # now real publish, then idempotent re-ingest
            rc, out = run('ingest', '--manifest', str(mp), '--source-root', str(src), '--store', str(store))
            assert rc == 0 and out['status'] == 'published'
            rc, out = run('ingest', '--manifest', str(mp), '--source-root', str(src), '--store', str(store))
            assert rc == 0 and out['status'] == 'idempotent', out
            # parent/child conflict
            pc = tmp / 'bad-pc.json'
            pc.write_text(json.dumps({'schema': 'westlake-artifact-release/v1', 'release_id': 'bad4',
                                      'files': [{'path': 'a', 'sha256': sha(b'm'), 'size': 1, 'mode': 420, 'role': 'x'},
                                                {'path': 'a/b', 'sha256': sha(b'm'), 'size': 1, 'mode': 420, 'role': 'x'}]}))
            rc, out = run('ingest', '--manifest', str(pc), '--source-root', str(src), '--store', str(store))
            assert rc != 0
        case('immutable_publish_interruption_idempotent_reentry', s4)


        # Scenario 5: source untouched by ingest; later source overwrite does not change CAS;
        # duplicate same-SHA re-ingest allowed; corrupted CAS fails even on idempotent retry.
        def s5():
            src = tmp / 's5src'
            payload = b'immutable-check' * 1000
            write(src / 'c.bin', payload, 0o644)
            st_before = os.stat(src / 'c.bin')
            mp, _ = make_manifest(tmp, src, [('c.bin', payload, 0o644)], rid='r5')
            store = tmp / 's5store'
            rc, out = run('ingest', '--manifest', str(mp), '--source-root', str(src), '--store', str(store))
            assert rc == 0 and out['status'] == 'published', out
            st_after = os.stat(src / 'c.bin')
            # original inode and mode and content unchanged by ingest
            assert st_before.st_ino == st_after.st_ino, (st_before.st_ino, st_after.st_ino)
            assert (st_after.st_mode & 0o7777) == 0o644
            assert (src / 'c.bin').read_bytes() == payload
            # later source overwrite must not change CAS object
            (src / 'c.bin').write_bytes(b'overwritten' * 100)
            op = store / 'objects' / 'sha256' / sha(payload)[:2] / sha(payload)
            assert op.read_bytes() == payload  # CAS unaffected by source overwrite
            rc, out = run('verify', '--manifest', str(mp), '--store', str(store))
            assert rc == 0
            # idempotent re-ingest of the SAME release manifest succeeds without re-reading sources
            rc, out = run('ingest', '--manifest', str(mp), '--source-root', str(src), '--store', str(store))
            assert rc == 0 and out['status'] == 'idempotent', out
            # corrupted CAS object fails even on an idempotent retry (objects re-verified first)
            os.chmod(op, 0o644); op.write_bytes(b'badbytes')
            rc, out = run('ingest', '--manifest', str(mp), '--source-root', str(src), '--store', str(store))
            assert rc != 0 and out['status'] == 'rejected', out
        case('source_untouched_overwrite_safe_idempotent_retry_rejects_corrupt_cas', s5)

        # Scenario 6: verify works on manifest + objects WITHOUT the releases record (remote cache fetch).
        def s6():
            store = tmp / 's6store'
            src = tmp / 's6src'
            write(src / 'n.bin', b'nocache', 0o644)
            mp, _ = make_manifest(tmp, src, [('n.bin', b'nocache', 0o644)], rid='r6')
            rc, out = run('ingest', '--manifest', str(mp), '--source-root', str(src), '--store', str(store))
            assert rc == 0
            (store / 'releases' / 'r6.json').unlink()  # simulate remote cache: objects only
            rc, out = run('verify', '--manifest', str(mp), '--store', str(store))
            assert rc == 0 and out['status'] == 'verified', out
            dest = tmp / 's6out'
            rc, out = run('restore', '--manifest', str(mp), '--store', str(store), '--dest', str(dest))
            assert rc == 0 and (dest / 'n.bin').read_bytes() == b'nocache'
        case('verify_restore_without_release_record', s6)

        # Scenario 7: symlink ancestor inside source-root rejected; mode >0777 rejected.
        def s7():
            src = tmp / 's7src'
            src.mkdir()
            real = tmp / 's7real'
            real.mkdir()
            write(real / 'deep.bin', b'deep', 0o644)
            (src / 'linkdir').symlink_to(real)
            mp, _ = make_manifest(tmp, src, [('linkdir/deep.bin', b'deep', 0o644)], rid='r7')
            rc, out = run('ingest', '--manifest', str(mp), '--source-root', str(src), '--store', str(tmp / 's7store'))
            assert rc != 0 and 'symlink ancestor' in out.get('error', ''), out
            mp2, _ = make_manifest(tmp, src, [], rid='r7b')
            doc = json.loads(mp2.read_text()); doc['files'] = [{'path': 'x', 'sha256': sha(b'x'), 'size': 1, 'mode': 0o1000, 'role': 'x'}]
            mp2.write_text(json.dumps(doc))
            rc, out = run('ingest', '--manifest', str(mp2), '--source-root', str(src), '--store', str(tmp / 's7store'))
            assert rc != 0 and 'mode' in out.get('error', ''), out
        case('symlink_ancestor_and_mode_over0777_rejected', s7)


        # Scenario 8: duplicate SHA across files deduped into one CAS object (large-file workload shape).
        def s8():
            src = tmp / 's8src'
            blob = b'dup-blob' * 10000
            write(src / 'one.bin', blob, 0o644)
            write(src / 'two.bin', blob, 0o600)
            mp, _ = make_manifest(tmp, src, [('one.bin', blob, 0o644), ('two.bin', blob, 0o600)], rid='r8')
            store = tmp / 's8store'
            rc, out = run('ingest', '--manifest', str(mp), '--source-root', str(src), '--store', str(store))
            assert rc == 0 and out['objects'] == 1, out  # one object for both
            dest = tmp / 's8out'
            rc, out = run('restore', '--manifest', str(mp), '--store', str(store), '--dest', str(dest))
            assert rc == 0
            assert (dest / 'one.bin').read_bytes() == blob and (dest / 'two.bin').read_bytes() == blob
            assert (os.stat(dest / 'one.bin').st_mode & 0o7777) == 0o644
            assert (os.stat(dest / 'two.bin').st_mode & 0o7777) == 0o600
        case('duplicate_sha_deduped_one_object', s8)

        # Scenario 9: symlink ancestor on store path rejected.
        def s9():
            src = tmp / 's9src'
            write(src / 'z.bin', b'z', 0o644)
            mp, _ = make_manifest(tmp, src, [('z.bin', b'z', 0o644)], rid='r9')
            linkdir = tmp / 's9link'
            linkdir.symlink_to(tmp / 's9real')
            (tmp / 's9real').mkdir()
            rc, out = run('ingest', '--manifest', str(mp), '--source-root', str(src), '--store', str(linkdir / 'store'))
            assert rc != 0 and 'symlink ancestor' in out.get('error', ''), out
        case('store_symlink_ancestor_rejected', s9)


        # Scenario 10: a pre-existing restore destination must be preserved (no-replace rename).
        def s10():
            src = tmp / 's10src'
            write(src / 'w.bin', b'wdata', 0o644)
            mp, _ = make_manifest(tmp, src, [('w.bin', b'wdata', 0o644)], rid='r10')
            store = tmp / 's10store'
            rc, out = run('ingest', '--manifest', str(mp), '--source-root', str(src), '--store', str(store))
            assert rc == 0
            dest = tmp / 's10out'
            # Simulate a dest that already holds unrelated content when restore is invoked.
            dest.mkdir()
            (dest / 'concurrent.txt').write_text('keep me')
            rc, out = run('restore', '--manifest', str(mp), '--store', str(store), '--dest', str(dest))
            assert rc != 0, out
            assert (dest / 'concurrent.txt').read_text() == 'keep me'
            assert not (dest / 'w.bin').exists()
            # sanity: restore to a genuinely new dest still works after the rejection
            dest2 = tmp / 's10out2'
            rc, out = run('restore', '--manifest', str(mp), '--store', str(store), '--dest', str(dest2))
            assert rc == 0 and (dest2 / 'w.bin').read_bytes() == b'wdata'
        case('preexisting_dest_preserved_no_replace_rename', s10)


        # Scenario 11: true race — a second thread materializes dest while restore is mid-flight.
        def s11():
            import threading, time
            src = tmp / 's11src'
            payload = b'race' * 10000
            write(src / 'r.bin', payload, 0o644)
            mp, _ = make_manifest(tmp, src, [('r.bin', payload, 0o644)], rid='r11')
            store = tmp / 's11store'
            rc, out = run('ingest', '--manifest', str(mp), '--source-root', str(src), '--store', str(store))
            assert rc == 0
            dest = tmp / 's11out'
            winner = {}
            def racer():
                time.sleep(0.05)  # aim into restore's temp-build window
                try:
                    dest.mkdir()
                    (dest / 'racer.txt').write_text('racer won')
                    winner['racer'] = True
                except FileExistsError:
                    winner['racer'] = False
            th = threading.Thread(target=racer)
            th.start()
            rc, out = run('restore', '--manifest', str(mp), '--store', str(store), '--dest', str(dest))
            th.join()
            if winner.get('racer'):
                # racer created dest first; restore must have been rejected and racer content kept
                assert rc != 0, out
                assert (dest / 'racer.txt').read_text() == 'racer won'
                assert not (dest / 'r.bin').exists()
            else:
                # restore finished first; racer mkdir failed FileExistsError; restore content present
                assert rc == 0 and (dest / 'r.bin').read_bytes() == payload, out
                assert not (dest / 'racer.txt').exists()
        case('restore_race_no_replace_keeps_first_writer', s11)

    print(json.dumps({'offline_only': True, 'passed': len(checks), 'checks': checks}))


if __name__ == '__main__':
    main()
