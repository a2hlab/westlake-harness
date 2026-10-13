import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tarfile
import time
import uuid


SERIAL = '5ea34a4500000000000000001123012c'
NOICE = 'com.github.ashutoshgngwr.noice'
NOICE_BEFORE = 'bbb21d7321668031774b5fc2e44ce632d7b2538853e09083a258f127631e845d'
NOICE_AFTER = '8e11b3136977e9f5dc897de85c26add9a219ea61884feabcbcd4e33566d5d2ca'
CERTIFICATE = '55afb1b9ecbc0d443be9cfa75459112c0da7672b774bc548bc4f38bc96ebbc23'


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def expand(path):
    return Path(os.path.expandvars(path))


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def pinned(pin):
    path = expand(pin['path'])
    need(path.is_file() and sha(path) == pin['sha256'], 'source pin drift: ' + str(path))
    return path


def names(text):
    lines = text.splitlines()
    need(bool(lines) and lines[0] == 'ID: 100:', 'BMS complete-list header missing')
    need(len(lines) > 1 and all(re.fullmatch(r'\t[A-Za-z][A-Za-z0-9_.]*', line) for line in lines[1:]),
         'BMS malformed, truncated or trailing list text')
    result = {line[1:] for line in lines[1:]}
    need(len(result) == len(lines) - 1, 'BMS duplicate package')
    return result


def expect_names(board, expected):
    _, text = board.shell('bm dump -a')
    need(names(text) == expected, 'BMS full set differs from pinned baseline plus this batch')


def apk_sha(board, package):
    path = '/data/app/el1/bundle/public/' + package + '/android/base.apk'
    _, text = board.shell('sha256sum ' + shlex.quote(path))
    match = re.fullmatch(r'([0-9a-f]{64})\s+' + re.escape(path), text.strip())
    need(match is not None, 'installed APK hash response malformed')
    return match[1]


def data_metadata(board, package):
    result = {}
    for prefix in ['el1/100/base', 'el2/100/base', 'el1/100/database', 'el2/100/log']:
        path = '/data/app/' + prefix + '/' + package
        quoted = shlex.quote(path)
        command = ('if test -L ' + quoted + '; then exit 2; elif test -d ' + quoted +
                   "; then printf 'PRESENT\\n'; stat -c '%d:%i:%u:%g:%a' " + quoted +
                   ' && ls -Zd ' + quoted + '; elif test -e ' + quoted +
                   "; then exit 3; else printf 'ABSENT\\n'; fi")
        _, text = board.shell(command)
        lines = text.splitlines()
        if lines == ['ABSENT']:
            result[path] = {'exists': False}
        else:
            need(len(lines) == 3 and lines[0] == 'PRESENT' and
                 re.fullmatch(r'\d+:\d+:\d+:\d+:[0-7]{3,4}', lines[1]), 'data-directory stat malformed')
            match = re.fullmatch(r'(u:object_r:[A-Za-z0-9_]+:s0)\s+' + re.escape(path), lines[2])
            need(match is not None, 'data-directory label malformed')
            result[path] = {'exists': True, 'dev_inode_uid_gid_mode': lines[1], 'label': match[1]}
    need(any(row['exists'] for row in result.values()), 'no data-directory preservation witness')
    return result


def data_files(board, metadata):
    result = {'files': {}, 'links': {}}
    for path, row in metadata.items():
        if not row['exists']:
            continue
        _, links = board.shell('find ' + shlex.quote(path) + ' -type l -print')
        for link in links.splitlines():
            need(link.startswith(path + '/') and link not in result['links'], 'malformed symlink inventory')
            _, target = board.shell('readlink ' + shlex.quote(link))
            need(bool(target) and '\n' not in target, 'symlink target incomplete')
            result['links'][link] = target
        child = 'sha256sum "$1" && stat -c \'%d:%i:%u:%g:%a\' "$1" && ls -Zd "$1"'
        _, text = board.shell('find ' + shlex.quote(path) + ' -type f -exec sh -c ' +
                              shlex.quote(child) + " sh '{}' ';'", timeout=180)
        lines = text.splitlines()
        need(len(lines) % 3 == 0, 'persistent file manifest incomplete')
        for number in range(0, len(lines), 3):
            match = re.fullmatch(r'([0-9a-f]{64})\s+(.+)', lines[number])
            need(match is not None and match[2].startswith(path + '/') and match[2] not in result['files'],
                 'persistent file SHA manifest malformed')
            label = re.fullmatch(r'(u:object_r:[A-Za-z0-9_]+:s0)\s+' + re.escape(match[2]), lines[number + 2])
            need(re.fullmatch(r'\d+:\d+:\d+:\d+:[0-7]{3,4}', lines[number + 1]) and label,
                 'persistent file ownership/label incomplete')
            result['files'][match[2]] = {'sha256': match[1], 'dev_inode_uid_gid_mode': lines[number + 1],
                                        'label': label[1]}
    return result


def verify_archive(path, metadata, contents):
    roots = {name.removeprefix('/data/app/'): row for name, row in metadata.items() if row['exists']}
    files = {name.removeprefix('/data/app/'): row for name, row in contents['files'].items()}
    links = {name.removeprefix('/data/app/'): target for name, target in contents['links'].items()}
    seen_files, seen_links, seen_roots, seen_names = set(), set(), set(), set()
    with tarfile.open(path, 'r:') as archive:
        for member in archive.getmembers():
            name = member.name.rstrip('/')
            need(name not in seen_names and not name.startswith('/') and '..' not in Path(name).parts and
                 any(name == root or name.startswith(root + '/') for root in roots), 'archive foreign/duplicate member')
            seen_names.add(name)
            if member.isdir():
                if name in roots:
                    seen_roots.add(name)
                    row = roots[name]
                else:
                    continue
            elif member.isfile() or member.islnk():
                need(name in files, 'archive unexpected regular file')
                if member.islnk():
                    need(member.linkname in files, 'archive foreign hardlink')
                payload = archive.extractfile(member)
                need(payload is not None and hashlib.sha256(payload.read()).hexdigest() == files[name]['sha256'],
                     'archive content does not match live file SHA')
                seen_files.add(name)
                row = files[name]
            elif member.issym():
                need(name in links and member.linkname == links[name], 'archive symlink differs')
                seen_links.add(name)
                continue
            else:
                raise ValueError('archive special member refused')
            fields = row['dev_inode_uid_gid_mode'].split(':')
            need((member.uid, member.gid, member.mode) == (int(fields[2]), int(fields[3]), int(fields[4], 8)),
                 'archive numeric owner/mode differs')
            labels = [value.rstrip('\0') for key, value in member.pax_headers.items() if key.endswith('security.selinux')]
            need(row['label'] in labels, 'archive SELinux label missing or different')
    need(seen_files == set(files) and seen_links == set(links) and seen_roots == set(roots),
         'archive missing live roots/files/links')


def enrich_archive(board, source, destination, metadata, contents):
    """Keep raw tar; encode only measured source metadata into a local PAX archive."""
    roots = {name.removeprefix('/data/app/') for name, row in metadata.items() if row['exists']}
    labels = {}
    with tarfile.open(source, 'r:') as original, tarfile.open(destination, 'w', format=tarfile.PAX_FORMAT) as target:
        for member in original.getmembers():
            name = member.name.rstrip('/')
            need(name not in labels and not name.startswith('/') and '..' not in Path(name).parts and
                 any(name == root or name.startswith(root + '/') for root in roots), 'raw archive foreign/duplicate member')
            need(member.isdir() or member.isfile() or member.issym() or member.islnk(), 'raw archive special member')
            path = '/data/app/' + name
            _, text = board.shell("stat -c '%d:%i:%u:%g:%a' " + shlex.quote(path) + ' && ls -Zd ' + shlex.quote(path))
            lines = text.splitlines()
            need(len(lines) == 2 and re.fullmatch(r'\d+:\d+:\d+:\d+:[0-7]{3,4}', lines[0]), 'member source stat incomplete')
            match = re.fullmatch(r'(u:object_r:[A-Za-z0-9_]+:s0)\s+' + re.escape(path), lines[1])
            need(match is not None, 'member source SELinux label incomplete')
            fields = lines[0].split(':')
            need((member.uid, member.gid, member.mode) == (int(fields[2]), int(fields[3]), int(fields[4], 8)),
                 'raw archive/source owner or mode mismatch')
            if member.isfile() or member.islnk():
                need(path in contents['files'], 'raw archive unexpected file')
                if member.islnk():
                    need('/data/app/' + member.linkname in contents['files'], 'foreign hardlink')
                payload = original.extractfile(member)
                need(payload is not None and hashlib.sha256(payload.read()).hexdigest() == contents['files'][path]['sha256'],
                     'raw archive/source content mismatch')
            elif member.issym():
                need(contents['links'].get(path) == member.linkname, 'raw archive/source symlink mismatch')
            labels[name] = {'dev_inode_uid_gid_mode': lines[0], 'label': match[1]}
            measured = copy.copy(member)
            measured.pax_headers = dict(member.pax_headers)
            measured.pax_headers['RHT.security.selinux'] = match[1]
            target.addfile(measured, original.extractfile(member) if member.isfile() else None)
    save(destination.parent / 'archive-source-metadata.json', labels)
    verify_archive(destination, metadata, contents)
    with tarfile.open(destination, 'r:') as final:
        need(len(final.getmembers()) == len(labels), 'derived archive membership changed')
        for member in final.getmembers():
            name = member.name.rstrip('/')
            need(member.pax_headers.get('RHT.security.selinux') == labels[name]['label'], 'derived label differs from source read')
    return labels


def private_archive(board, directory, metadata, contents):
    remote = '/data/local/tmp/wl-noice-backup-' + uuid.uuid4().hex
    board.shell('umask 077; mkdir ' + shlex.quote(remote))
    roots = [path.removeprefix('/data/app/') for path, row in metadata.items() if row['exists']]
    archive_path = remote + '/data.tar'
    # OH tar --selinux crashes in getfilecon on both relative and absolute paths.
    # Preserve its plain raw archive, then bind measured labels in local PAX metadata.
    board.shell('tar --numeric-owner -cf ' + shlex.quote(archive_path) +
                ' -C /data/app ' + ' '.join(shlex.quote(path) for path in roots), timeout=180)
    _, text = board.shell('sha256sum ' + shlex.quote(archive_path))
    match = re.fullmatch(r'([0-9a-f]{64})\s+' + re.escape(archive_path), text.strip())
    need(match is not None, 'remote private archive SHA malformed')
    raw = directory / 'data-original.tar'
    board.receive(archive_path, raw)
    need(not raw.is_symlink(), 'local archive symlink refused')
    raw.chmod(0o600)
    need(sha(raw) == match[1], 'remote/local raw archive SHA mismatch')
    local = directory / 'data.tar'
    labels = enrich_archive(board, raw, local, metadata, contents)
    local.chmod(0o600)
    need(metadata == data_metadata(board, NOICE) and contents == data_files(board, metadata),
         'Noice data changed while backing up; no update')
    save(directory / 'private-archive.json', {'remote_original': archive_path, 'local_original': str(raw),
         'original_sha256': sha(raw), 'local': str(local), 'sha256': sha(local), 'readable': True,
         'label_source': 'actual per-member stat and ls -Zd command receipts', 'labelled_members': len(labels),
         'source_metadata_sha256': sha(directory / 'archive-source-metadata.json'),
         'scope': 'four app data roots; measured labels encoded locally; no extraction or removal'})


def bundle(board, batch, package, path):
    _, text = board.shell('bm dump -n ' + shlex.quote(package))
    Path(path).write_text(text + '\n')
    result = batch.parse_bundle(text, package)
    need(result.get('queryable') is True and isinstance(result.get('uid'), int), 'unambiguous installed UID required')
    document = json.loads(text[text.index('{'):])
    info = document['applicationInfo']
    need(type(document.get('gid')) is int and document['gid'] >= 0 and info.get('uid') == result['uid'],
         'actual GID/application UID missing or ambiguous')
    for field in ['accessTokenId', 'accessTokenIdEx']:
        need(type(info.get(field)) is int and info[field] > 0, 'actual token field missing: ' + field)
    permissions = document['reqPermissions']
    states = document['reqPermissionStates']
    need(isinstance(permissions, list) and all(isinstance(value, str) for value in permissions) and
         len(set(permissions)) == len(permissions) and isinstance(states, list) and len(states) == len(permissions),
         'actual projected permissions/states incomplete')
    result.update(gid=document['gid'], accessTokenId=info['accessTokenId'], accessTokenIdEx=info['accessTokenIdEx'],
                  permission_states=dict(zip(permissions, states)))
    return result


def run_adapter(config, app, directory, deadline):
    remaining = deadline - time.monotonic()
    need(remaining > 30, 'installation budget exhausted; no next package')
    env = dict(os.environ, DEMO_T3_MODE='install')
    argv = [sys.executable, str(pinned(config['adapter'])), '--execute', '--manifest',
            str(pinned(config['manifest'])), '--input-root', str(expand(app['input_root'])),
            '--keys', app['key'], '--serial', SERIAL, '--lane', 'outer(codex)', '--out', str(directory / 'install')]
    save(directory / 'adapter-argv.json', {'argv': argv, 'mode': 'install-only', 'uninstall_fallback': False})
    with (directory / 'install.stdout.txt').open('w') as stdout, (directory / 'install.stderr.txt').open('w') as stderr:
        result = subprocess.run(argv, env=env, stdout=stdout, stderr=stderr, timeout=min(300, remaining))
    save(directory / 'adapter-exit.json', {'exit_code': result.returncode})
    need(result.returncode == 0, 'original adapter failed; preserve evidence, no retry/uninstall/data cleanup')
    records = list((directory / 'install').glob('**/' + app['key'] + '/record.json'))
    need(len(records) == 1, 'one actual install record required')
    record = read(records[0])
    need(record.get('status') == 'installed' and record.get('serial') == SERIAL and
         record.get('package') == app['package'] and record.get('apk_sha256') == app['apk_sha256'],
         'actual install receipt identity differs')
    return {'success': True, 'serial': SERIAL, 'apk_sha256': app['apk_sha256'],
            'record': str(records[0]), 'record_sha256': sha(records[0])}


def perform(board, batch, config, operation, directory, expected, installer):
    app = operation['app']
    package = app['package']
    need(operation['kind'] == 'noice-upgrade' and package == NOICE and app['apk_sha256'] == NOICE_AFTER,
         'only explicit Noice upgrade allowed')
    expect_names(board, expected)
    need(package in expected and apk_sha(board, package) == NOICE_BEFORE, 'Noice actual preimage differs')
    before = bundle(board, batch, package, directory / 'bundle-before.txt')
    need(all(before[key] == value for key, value in config['expected_identity'].items()),
         'Noice actual UID/GID/token differs from root readonly evidence')
    need(batch.cold_stop(board, package, before['uid'], directory, 'noice-pre-backup'),
         'exact Noice cold-stop refused; no update')
    metadata = data_metadata(board, package)
    need(metadata == config['expected_data_metadata'], 'Noice directory preimage differs from root readonly evidence')
    save(directory / 'data-before.json', metadata)
    contents = data_files(board, metadata)
    save(directory / 'files-before.json', contents)
    counts = {path: sum(name.startswith(path + '/') for name in contents['files']) for path in metadata}
    need(counts == config['expected_file_counts'], 'Noice pre-update file counts differ from actual root probe')
    backup = directory / 'original-base.apk'
    board.receive('/data/app/el1/bundle/public/' + package + '/android/base.apk', backup)
    need(not backup.is_symlink(), 'local APK backup symlink refused')
    backup.chmod(0o600)
    need(sha(backup) == NOICE_BEFORE and apk_sha(board, package) == NOICE_BEFORE,
         'Noice persistent backup or second live hash differs; no update')
    save(directory / 'backup.json', {'path': str(backup), 'sha256': sha(backup),
                                    'uid': before['uid'], 'remote_restore_executed': False})
    private_archive(board, directory, metadata, contents)
    receipt = installer(config, app, directory)
    need(apk_sha(board, package) == app['apk_sha256'], 'installed APK differs after original adapter')
    after = bundle(board, batch, package, directory / 'bundle-after.txt')
    after_metadata = data_metadata(board, package)
    save(directory / 'data-after.json', after_metadata)
    need(before['uid'] == after['uid'], 'Noice UID changed; STOP without data cleanup')
    for field in ['gid', 'accessTokenId', 'accessTokenIdEx', 'permission_states']:
        need(before[field] == after[field], 'Noice identity/permission state changed: ' + field)
    need(metadata == after_metadata, 'Noice data-directory metadata changed; STOP without rollback/uninstall')
    after_contents = data_files(board, after_metadata)
    save(directory / 'files-after.json', after_contents)
    need(contents == after_contents, 'Noice persistent file contents changed; STOP without cleanup')
    expect_names(board, expected)
    return receipt


def identity(config, out):
    argv = ['orb', '-m', 'a2hlab', 'env', 'WORKSPACES=' + os.environ['WORKSPACES'],
            'MAC_HOME=' + os.environ.get('MAC_HOME', str(Path.home())), 'python3',
            str(pinned(config['identity'])), '--round', str(expand(config['round'])), '--out', str(out)]
    subprocess.run(argv, check=True, timeout=180)


def validate(config):
    need(config['serial'] == SERIAL, 'only authorized spare5ea')
    for key in ['batch', 'adapter', 'manifest', 'identity', 'baseline_names', 'certificate_evidence',
                'live_bundle_evidence', 'root_data_probe']:
        pinned(config[key])
    live = read(pinned(config['live_bundle_evidence']))
    need(live['name'] == NOICE and live['versionCode'] == 66 and live['versionName'] == '2.5.1' and
         config['expected_identity'] == {'uid': live['uid'], 'gid': live['gid'],
             'accessTokenId': live['applicationInfo']['accessTokenId'],
             'accessTokenIdEx': live['applicationInfo']['accessTokenIdEx']}, 'Noice live typed identity differs')
    certificate = read(pinned(config['certificate_evidence']))
    need(certificate['before']['apk_sha256'] == NOICE_BEFORE and
         certificate['after']['apk_sha256'] == NOICE_AFTER and
         certificate['before']['certificate_sha256'] == certificate['after']['certificate_sha256'] == [CERTIFICATE],
         'Noice same-certificate upgrade evidence differs')
    operation = config['operation']
    need(operation['kind'] == 'noice-upgrade' and operation['app']['package'] == NOICE and
         operation['app']['apk_sha256'] == NOICE_AFTER and pinned(operation['apk']) ==
         expand(operation['app']['apk']), 'fixed Noice APK source differs')
    pinned(config['original_apk'])
    need(config['original_apk']['sha256'] == NOICE_BEFORE, 'original Noice source differs')
    need(certificate['before']['source'] == config['original_apk'] and
         certificate['after']['source'] == operation['apk'] and
         certificate['before']['package'] == certificate['after']['package'] == NOICE and
         certificate['before']['version_code'] == 66 and certificate['after']['version_code'] == 72,
         'same-certificate APK roles or version sequence differ')
    manifest = read(pinned(config['manifest']))
    need(manifest['apps'] == [operation['app']], 'manifest must select only the exact Noice app')


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--allow-noice-update', action='store_true')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    config = read(args.config)
    validate(config)
    if not args.execute:
        print(json.dumps({'execution': 'not-requested', 'device_calls': 0,
                          'package': NOICE, 'noice_requires_explicit_flag': True}))
        return 0
    need(args.allow_noice_update, 'explicit Noice update flag required')
    private_root = Path(os.environ['WORKSPACES']) / 'westlake-inputs/private-backups/noice-20261013'
    need(args.out.parent.resolve() == private_root.resolve(), 'evidence and data must be in authorized private backup root')
    os.umask(0o077)
    private_root.mkdir(parents=True, mode=0o700, exist_ok=True)
    need(not private_root.is_symlink() and private_root.stat().st_mode & 0o077 == 0, 'private backup root must be0700')
    need(not args.out.exists() and not args.out.is_symlink(), 'fresh persistent evidence/backup output required')
    args.out.mkdir(parents=True, mode=0o700)
    spec = importlib.util.spec_from_file_location('original_bms', pinned(config['batch']))
    batch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(batch)
    board = batch.Board(SERIAL, 'hdc', str(expand(config['lock_cmd'])), 'outer(codex)', args.out / 'commands')
    records = {}
    deadline = time.monotonic() + 1800
    report = {'status': 'STARTED', 'uninstall_fallback': False, 'runtime_modified': False}
    try:
        identity(config, args.out / 'identity-before')
        board.ready()
        need(board.boot.strip() == config['boot_id'], 'actual boot changed')
        expected = names(pinned(config['baseline_names']).read_text())
        expect_names(board, expected)
        operation = config['operation']
        directory = args.out / operation['app']['key']
        directory.mkdir(mode=0o700)
        records[operation['app']['key']] = perform(board, batch, config, operation, directory, expected,
                                                  lambda conf, app, folder: run_adapter(conf, app, folder, deadline))
        save(args.out / 'actual-install-index.json', records)
        report['status'] = 'INSTALL_RECEIPT_COMPLETE_PENDING_FINAL_IDENTITY'
    except Exception as error:
        report.update(status='STOP_PRESERVE_EVIDENCE_NO_RETRY', error=str(error))
    try:
        identity(config, args.out / 'identity-after')
        report['identity_after_exit'] = 0
    except Exception as error:
        report.update(status='STOP_PRESERVE_EVIDENCE_NO_RETRY', identity_after_error=str(error))
    if report['status'] == 'INSTALL_RECEIPT_COMPLETE_PENDING_FINAL_IDENTITY':
        report['status'] = 'VERIFIED_INSTALL_NOT_UI_SIGNOFF'
    save(args.out / 'result.json', dict(report, records=records))
    return 0 if report['status'] == 'VERIFIED_INSTALL_NOT_UI_SIGNOFF' else 1


if __name__ == '__main__':
    raise SystemExit(main())
