#!/usr/bin/env python3
import datetime, hashlib, json, os, pathlib, shlex, stat, subprocess, tarfile, time, uuid
HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = HERE/'.artifacts/staging'
NAMES = ['closed-round-regular-files', '128-link-map', 'eight-fixed-window-receipts']
ART = HERE / '.artifacts'
ART.mkdir(exist_ok=True)
started = datetime.datetime.now().astimezone().isoformat()
result = {'status': 'in_progress', 'started_at': started, 'device_calls': 0, 'source': '$WORKSPACES/' + str(SOURCE.relative_to(ROOT.parent)), 'directories': NAMES, 'scope': 'Closed actual61b original round regular files and exact128 link map; eight existing raw window archives reused. No device collector, peer comparison JPEG, active index or final signoff included.', 'UI_verdict': 'not_adjudicated_by_archiver'}
def save():
    (HERE / 'results.json').write_text(json.dumps(result, indent=2) + '\n')
def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()
def inventory():
    rows = []
    if True:
        for p in sorted(SOURCE.rglob('*')):
            s = p.lstat()
            if stat.S_ISDIR(s.st_mode):
                continue
            if not stat.S_ISREG(s.st_mode):
                raise RuntimeError(f'nonregular path refused: {p.relative_to(SOURCE)}')
            rel = str(p.relative_to(SOURCE))
            if any(x in rel.lower() for x in ('noice-private', 'noice-data')):
                raise RuntimeError(f'private-backup-like path refused: {rel}')
            rows.append({'path': rel, 'bytes': s.st_size, 'sha256': digest(p), 'mode': stat.S_IMODE(s.st_mode), 'mtime_ns': s.st_mtime_ns, 'ctime_ns': s.st_ctime_ns, 'inode': s.st_ino})
    return rows
def run(label, argv, *, stdin=None):
    with (HERE/(label+'.stdout.txt')).open('wb') as out, (HERE/(label+'.stderr.txt')).open('wb') as err:
        p = subprocess.run(argv, stdin=stdin, stdout=out, stderr=err, timeout=900)
    result[label+'_rc'] = p.returncode
    save()
    if p.returncode:
        raise RuntimeError(f'{label} rc={p.returncode}; see original stdout/stderr')
    return (HERE/(label+'.stdout.txt')).read_text()
try:
    prepared = json.loads((HERE/'prepared.json').read_text())
    assert prepared['status'] == 'STAGING_COMPLETE_NOT_YET_ARCHIVED'
    assert prepared['source_unchanged'] and prepared['all_selected_archive_members_verified']
    result.update(source_date='2026-10-14', link_count=prepared['link_count'], window_archives=8,
                  driver_exit_code=None, comparison_jpeg_scope=prepared['comparison_jpeg_scope'])
    save()
    print('HASHING_BEFORE', flush=True)
    before = inventory()
    manifest = ART/'source-manifest.jsonl'
    manifest.write_text(''.join(json.dumps(x, separators=(',',':'))+'\n' for x in before))
    result.update(files=len(before), source_bytes=sum(x['bytes'] for x in before), source_manifest_sha256=digest(manifest), symlinks=0, private_backup_included=False)
    save()
    archive = ART/'full128-round-supplement.tar.gz'
    if archive.exists():
        raise RuntimeError('archive already exists; refuse overwrite')
    print(f'PACKAGING {len(before)} files', flush=True)
    with tarfile.open(archive, 'w:gz', compresslevel=6) as tar:
        for row in before:
            tar.add(SOURCE/row['path'], arcname=row['path'], recursive=False)
        tar.add(manifest, arcname='__archive_meta__/source-manifest.jsonl', recursive=False)
    print('VERIFYING_MEMBERS', flush=True)
    expected = {r['path']: r for r in before}
    seen = set()
    with tarfile.open(archive, 'r:gz') as tar:
        for member in tar:
            f = tar.extractfile(member)
            assert f is not None
            h = hashlib.sha256()
            total = 0
            for block in iter(lambda: f.read(1024*1024), b''):
                total += len(block); h.update(block)
            if member.name == '__archive_meta__/source-manifest.jsonl':
                assert total == manifest.stat().st_size and h.hexdigest() == result['source_manifest_sha256']
                continue
            assert member.name in expected and member.name not in seen
            row = expected[member.name]
            assert total == row['bytes'] and h.hexdigest() == row['sha256'], member.name
            seen.add(member.name)
    assert seen == set(expected)
    result['archive_members_verified'] = True
    print('HASHING_AFTER', flush=True)
    after = inventory()
    assert before == after, 'source changed during packaging'
    import runpy
    helper = runpy.run_path(str(HERE/'prepare.py'))
    originals = json.loads((SOURCE/'source-snapshot.json').read_text())
    for row in originals:
        p = ROOT.parent/row['path'].removeprefix('$WORKSPACES/')
        assert helper['entry'](p) == row, 'original source changed'
    selected, links = helper['shape']()
    assert links == json.loads((SOURCE/'source-link-snapshot.raw.json').read_text())
    assert [helper['entry'](p) for p in selected] == prepared['regular_sources']
    result['source_unchanged'] = True
    result['original_source_unchanged_through_packaging'] = True
    result.update(sha256=digest(archive), bytes=archive.stat().st_size)
    run('gzip-test', ['gzip','-t',str(archive)])
    previous = json.loads((ROOT/'benchmark/2026-10-13-fresh487-archive/archive.json').read_text())['archive']
    host, old = previous.split(':', 1)
    assert host == 'hw248'
    remote_parent = pathlib.PurePosixPath(old).parent.parent
    dirname = 'westlake-final61b-round-supplement-'  + datetime.datetime.now().strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    remote_dir = remote_parent/dirname
    remote = remote_dir/'full128-round-supplement.tar.gz'
    result['archive'] = host+':'+str(remote)
    print('REMOTE_CREATE', flush=True)
    run('remote-create', ['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',host,'mkdir -- '+shlex.quote(str(remote_dir))])
    print('REMOTE_UPLOAD', flush=True)
    with archive.open('rb') as f:
        run('remote-upload', ['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',host,'set -C; cat > '+shlex.quote(str(remote))],stdin=f)
    print('REMOTE_VERIFY', flush=True)
    remote_script = "import pathlib,hashlib,json,gzip; p=pathlib.Path("+repr(str(remote))+"); h=hashlib.sha256(); f=p.open('rb'); [h.update(x) for x in iter(lambda:f.read(1048576),b'')]; f.close(); print(json.dumps({'sha256':h.hexdigest(),'bytes':p.stat().st_size}))"
    remote_receipt = run('remote-verify', ['ssh','-o','BatchMode=yes','-o','ConnectTimeout=15',host,'gzip -t -- '+shlex.quote(str(remote))+' && python3 -c '+shlex.quote(remote_script)])
    observed = json.loads(remote_receipt)
    assert observed == {'sha256':result['sha256'],'bytes':result['bytes']}
    result.update(status='complete', verified_remote=True, finished_at=datetime.datetime.now().astimezone().isoformat())
    save()
    (HERE/'archive.json').write_text(json.dumps({k:result[k] for k in ['archive','sha256','bytes','verified_remote','files','source_bytes','source_manifest_sha256','archive_members_verified','source_unchanged','scope','private_backup_included']},indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['status','archive','sha256','bytes','files']}), flush=True)
except Exception as exc:
    result.update(status='failed', error=f'{type(exc).__name__}: {exc}')
    save()
    raise
