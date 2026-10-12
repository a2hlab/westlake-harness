#!/usr/bin/env python3
"""One explicitly authorized empty-directory supplement; no content removal."""
import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time
import uuid

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
SERIAL = '5cd1e3dd00000000000000000923012c'
ROOT = '/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d'
TARGET = ROOT + '/webview-t-data'
META = dict(mode='755', uid=20011300, gid=20011300, label='u:object_r:appdat:s0')
SOURCE_META = dict(META, uid=20011206, gid=20011206)
ORIGIN_SHA = 'dfd4e5c242b9327ab07a29abf4f2c9ef9640097078703ae4a811cceab7d35f7c'
EXECUTOR_SHA = '496fa979f4af71b8c01c44a474aed4074b64544d5d1eb500709c649679831d0d'
SHA = re.compile(r'[0-9a-f]{64}\Z')
BOOT = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\Z')
IDENTITY = re.compile(r'[0-9]+:[0-9]+\Z')
q = shlex.quote


def need(ok, why):
    if not ok:
        raise ValueError(why)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def resolve(value, base):
    workspace = os.environ.get('WORKSPACES', str(HERE.parents[3]))
    path = Path(str(value).replace('$WORKSPACES', workspace)).expanduser()
    return path.resolve() if path.is_absolute() else (Path(base) / path).resolve()


def pin(ref, base):
    need(isinstance(ref, dict) and SHA.fullmatch(str(ref.get('sha256', ''))), 'typed SHA pin required')
    path = resolve(ref['path'], base)
    need(path.is_file() and digest(path) == ref['sha256'], 'pinned file missing/drift: ' + str(path))
    return path


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2); stream.write('\n'); stream.flush(); os.fsync(stream.fileno())


def validate(manifest_path, manifest_sha, authorization_path, authorization_sha, serial, boot, action, now=None):
    base = Path(manifest_path).resolve().parent
    manifest = read(pin(dict(path=str(Path(manifest_path).resolve()), sha256=manifest_sha), base))
    need(manifest.get('schema') == 'exact-directory-supplement/v1', 'manifest schema')
    need(manifest.get('executor_sha256') == digest(__file__), 'executor independent self pin')
    need(manifest.get('execution_enabled') is False, 'supplement manifest must remain a candidate')
    need(manifest.get('synthetic') is False, 'actual execution rejects synthetic manifest')
    need(manifest.get('serial') == serial == SERIAL, 'serial mismatch')
    need(BOOT.fullmatch(boot) and manifest.get('boot_id') == boot, 'current boot mismatch')
    need(manifest.get('target') == TARGET and manifest.get('before') == {'exists': False}, 'single absent target scope')
    need(manifest.get('after') == META and manifest.get('source_metadata') == SOURCE_META, 'directory metadata/UID projection')
    for name in ('source_receipt', 'source_stdout', 'source_stderr', 'target_receipt', 'target_stdout', 'target_stderr'):
        pin(manifest['evidence'][name], base)
    for prefix in ('source', 'target'):
        record = read(pin(manifest['evidence'][prefix + '_receipt'], base))
        need(type(record.get('exit')) is int and record['exit'] == 0, 'historical transport failed')
        expected_serial = '61b0657200000000000000000324012c' if prefix == 'source' else SERIAL
        need(record.get('argv', [])[1:4] == ['-t', expected_serial, 'shell'], 'historical transport argv/serial mismatch')
        for kind in ('stdout', 'stderr'):
            need(record.get(kind + '_sha256') == manifest['evidence'][prefix + '_' + kind]['sha256'], 'historical raw pin mismatch')
        need(pin(manifest['evidence'][prefix + '_stderr'], base).read_bytes() == b'', 'historical transport stderr nonempty')
        need(pin(manifest['evidence'][prefix + '_stdout'], base).read_text().rstrip().endswith('RE_REMOTE_RC=0'), 'historical remote status missing/nonzero')
    source = pin(manifest['evidence']['source_stdout'], base).read_text()
    boots = [line for line in source.splitlines() if BOOT.fullmatch(line)]
    need(len(boots) == 2 and boots[0] == boots[1] and source.splitlines()[0] == boots[0], 'source boot evidence unstable/missing')
    need(source.splitlines().count('755 20011206 20011206 directory') == 1, 'source directory stat absent')
    source_rows = [line.split() for line in source.splitlines() if line.rstrip().endswith(' ' + TARGET)]
    need(len(source_rows) == 1 and source_rows[0][0] == 'drwxr-xr-x' and source_rows[0][2:5] == ['20011206','20011206',META['label']], 'source directory ls identity')
    target_raw = pin(manifest['evidence']['target_stdout'], base).read_text()
    need(target_raw.splitlines()[0] == boot and '20011300:20011300' in target_raw.splitlines(), 'historical target boot/owner mismatch')
    need('ls: ' + TARGET + ': No such file or directory' in target_raw, 'historical explicit directory absence missing')
    origin_path = pin(manifest['origin_realization'], base); origin = read(origin_path)
    need(digest(origin_path) == ORIGIN_SHA, 'original pinned 487 proof differs')
    need(origin.get('schema') == 'exact-realization/v1' and origin.get('route_targets') == 487, 'origin 487 proof required')
    need(origin['parameters']['serial'] == SERIAL and origin['parameters']['host_uid'] == META['uid'] and origin['parameters']['host_gid'] == META['gid'], 'origin host identity mismatch')
    executor = pin(manifest['tools']['executor'], base)
    need(digest(executor) == EXECUTOR_SHA == origin['executor_sha256'], 'frozen executor drift')
    plan_path = origin_path.parent / 'package/plan.json'
    need(digest(plan_path) == origin['plan_sha256'], 'origin plan drift')
    plan = read(plan_path)
    driver = pin(manifest['tools']['driver'], base)
    need(digest(driver) == plan['tools']['driver']['sha256'], 'origin transport driver drift')
    auth = read(pin(dict(path=str(Path(authorization_path).resolve()), sha256=authorization_sha), base))
    need(auth.get('schema') == 'exact-directory-authorization/v1' and auth.get('approved_by') == 'outer(codex)', 'independent outer authorization required')
    for key, expected in dict(manifest_sha256=manifest_sha, executor_sha256=digest(__file__), serial=serial, boot_id=boot, action=action).items():
        need(auth.get(key) == expected, 'authorization mismatch: ' + key)
    need(auth.get('synthetic', False) is False, 'synthetic authorization cannot execute')
    expiry = auth.get('expires_epoch')
    need(type(expiry) in (int, float) and math.isfinite(expiry) and expiry > (time.time() if now is None else now), 'authorization expired')
    need(isinstance(auth.get('holder'), str) and auth['holder'], 'external holder required')
    auth['_lock_path'] = str(pin(auth['lock_tool'], Path(authorization_path).resolve().parent))
    manifest['_sha256'] = manifest_sha
    return manifest, auth, executor, driver


class CommandError(ValueError):
    pass


class Device:
    """Reuse the frozen executor's raw Transport; preserve both real exit codes."""
    def __init__(self, executor, driver, hdc, out):
        need(Path(hdc).is_file() and os.access(hdc, os.X_OK), 'explicit local HDC required')
        spec = importlib.util.spec_from_file_location('r4_frozen_executor_transport', executor)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        old = module.Device({'tools': {'driver': {'path': str(driver)}}, 'hdc': hdc, 'serial': SERIAL}, out)
        self.transport, self.hdc, self.steps = old.transport, str(hdc), []

    def shell(self, name, script):
        marker = '__R4_RC_' + uuid.uuid4().hex + '__'
        command = '/system/bin/sh -c ' + q(script) + '; r4rc=$?; printf "\\n' + marker + '%s\\n" "$r4rc"'
        step = {'name': name, 'script': script, 'transport_rc': None, 'remote_rc': None}
        self.steps.append(step)
        try:
            rc, text = self.transport.run(name, [self.hdc, '-t', SERIAL, 'shell', command])
            step['transport_rc'] = rc
            text = text.replace('\r', '')
            match = re.search(r'\n' + re.escape(marker) + r'([0-9]+)\n?\Z', text)
            step['remote_rc'] = int(match[1]) if match else None
            need(rc == 0 and match and int(match[1]) == 0, name + ' transport/remote failure')
            return text[:match.start()].rstrip('\n')
        except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
            step['error'] = str(exc)
            raise CommandError(str(exc)) from exc


def guard(boot, path):
    return ('set -eu\ntest "$(cat /proc/sys/kernel/random/boot_id)" = ' + q(boot) + '\np=' + q(path) +
            '\nwalk="$p"; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done\n')


def probe(dev, path, boot):
    script = guard(boot, path) + '''if [ -e "$p" ]; then
 test -d "$p"
 first=$(stat -c '%d:%i' "$p")
 echo EXISTS
 stat -c '%a %u %g' "$p"
 ls -ldnZ "$p"
 echo "$first"
 test "$(stat -c '%d:%i' "$p")" = "$first"
else
 test -d "$(dirname "$p")"; test -r "$(dirname "$p")"; test -x "$(dirname "$p")"
 echo ABSENT
fi'''
    lines = dev.shell('probe-directory', script).splitlines()
    if lines == ['ABSENT']:
        return {'exists': False}
    need(len(lines) == 4 and lines[0] == 'EXISTS', 'unknown directory probe')
    mode, uid, gid = lines[1].split()
    fields = lines[2].split(); labels = [field for field in fields if field.startswith('u:object_r:')]
    need(fields[0].startswith('d') and fields[-1] == path and len(labels) == 1 and IDENTITY.fullmatch(lines[3]), 'unknown directory identity/label')
    need(re.fullmatch('[0-7]{3,4}', mode) and uid.isdigit() and gid.isdigit(), 'unknown directory metadata')
    return dict(exists=True, mode=mode, uid=int(uid), gid=int(gid), label=labels[0], identity=lines[3])


def metadata(row):
    return {key: row[key] for key in META}


def owned_guard(boot, identity):
    need(IDENTITY.fullmatch(identity), 'invalid owned inode')
    return guard(boot, TARGET) + 'test -d "$p"\ntest "$(stat -c \'%d:%i\' "$p")" = ' + q(identity) + '\n'


def transaction(manifest, dev, out, action, authorization):
    """Fake transports may exercise this primitive; CLI authority is separate."""
    out = Path(out); boot = manifest['boot_id']; manifest_sha = manifest['_sha256']
    receipt = {'schema': 'exact-directory-transaction-receipt/v1', 'action': action, 'target': TARGET,
               'manifest_sha256': manifest_sha, 'serial': SERIAL, 'boot_id': boot,
               'device_content_deleted': False, 'executor_rc': None, 'steps': dev.steps}
    identity = None
    try:
        parent = probe(dev, ROOT, boot)
        need(parent['exists'] and metadata(parent) == META, 'runtime parent metadata drift')
        if action == 'apply':
            need(not out.exists(), 'fresh transaction directory required')
            out.mkdir(parents=True)
            current = probe(dev, TARGET, boot)
            if current['exists']:
                need(metadata(current) == META, 'existing directory metadata drift')
                receipt.update(state='ALREADY_EQUAL', executor_rc=0, created=False)
            else:
                intent = {'schema': 'exact-directory-intent/v1', 'manifest_sha256': manifest_sha,
                          'serial': SERIAL, 'boot_id': boot, 'target': TARGET, 'before': {'exists': False}}
                save(out / 'intent.json', intent)
                script = guard(boot, TARGET) + 'test ! -e "$p"\nmkdir "$p"\nstat -c \'%d:%i\' "$p"'
                identity = dev.shell('mkdir-single', script).strip()
                need(IDENTITY.fullmatch(identity), 'mkdir ownership readback unknown')
                save(out / 'owned.json', dict(intent, identity=identity))
                current = probe(dev, TARGET, boot)
                need(current['exists'] and current['identity'] == identity, 'created directory replaced')
                save(out / 'checkpoint-0.json', current)
                commands = [('chown', 'chown 20011300:20011300 "$p"'), ('chmod', 'chmod 755 "$p"'), ('chcon', 'chcon u:object_r:appdat:s0 "$p"')]
                for number, (name, command) in enumerate(commands, 1):
                    dev.shell(name, owned_guard(boot, identity) + command)
                    current = probe(dev, TARGET, boot)
                    need(current['exists'] and current['identity'] == identity, 'directory replaced during metadata mutation')
                    save(out / ('checkpoint-%d.json' % number), current)
                need(metadata(current) == META, 'final directory metadata readback differs')
                save(out / 'journal.json', dict(intent, identity=identity, metadata=metadata(current)))
                receipt.update(state='CREATED_VERIFIED', executor_rc=0, created=True, journal_sha256=digest(out / 'journal.json'))
        else:
            need(action == 'rollback' and out.is_dir(), 'existing transaction required for rollback')
            journal_path = out / 'journal.json'
            need(digest(journal_path) == authorization.get('journal_sha256'), 'rollback journal independent pin')
            journal = read(journal_path); intent = read(out / 'intent.json'); owned = read(out / 'owned.json')
            expected = {'schema': 'exact-directory-intent/v1', 'manifest_sha256': manifest_sha,
                        'serial': SERIAL, 'boot_id': boot, 'target': TARGET, 'before': {'exists': False}}
            need(intent == expected and owned == dict(expected, identity=journal['identity']), 'unknown transaction ownership')
            need({k: journal[k] for k in expected} == expected, 'rollback manifest/target binding')
            current = probe(dev, TARGET, boot)
            need(current['exists'] and current['identity'] == journal['identity'] and metadata(current) == journal['metadata'], 'rollback identity/metadata drift; preserve directory')
            meta = journal['metadata']
            need(set(meta) == set(META) and re.fullmatch('[0-7]{3,4}', meta['mode']) and type(meta['uid']) is int and type(meta['gid']) is int and re.fullmatch(r'u:object_r:[A-Za-z0-9_]+:s0',meta['label']), 'journal metadata invalid')
            script = owned_guard(boot, journal['identity'])
            script += 'test "$(stat -c \'%a %u %g\' "$p")" = ' + q('%s %s %s' % (meta['mode'], meta['uid'], meta['gid'])) + '\n'
            script += 'ls -ldnZ "$p" | grep -F ' + q(' ' + meta['label'] + ' ') + ' >/dev/null\nrmdir "$p"'
            dev.shell('rmdir-owned-empty-only', script)
            need(probe(dev, TARGET, boot) == {'exists': False}, 'rollback absence readback failed')
            receipt.update(state='ROLLED_BACK_EMPTY_DIRECTORY', executor_rc=0, created=True)
            save(out / 'rollback.json', receipt)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        receipt.update(state='FAILED_PRESERVED_RETRY_REQUIRES_AUTHORIZATION', executor_rc=1, error=str(exc))
        if action == 'apply' and identity and IDENTITY.fullmatch(identity) and (out / 'owned.json').exists() and not (out / 'journal.json').exists():
            try:
                current = probe(dev, TARGET, boot)
                need(current['exists'] and current['identity'] == identity, 'failed mutation ownership unknown')
                save(out / 'journal.json', dict(read(out / 'intent.json'), identity=identity, metadata=metadata(current)))
                receipt['journal_sha256'] = digest(out / 'journal.json')
            except (OSError, ValueError, KeyError, TypeError) as probe_error:
                receipt['ownership_recovery_error'] = str(probe_error)
        if out.is_dir():
            save(out / ('failure-' + uuid.uuid4().hex + '.json'), receipt)
    if out.is_dir() and action == 'apply' and receipt['executor_rc'] == 0:
        save(out / 'applied.json', receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('manifest', 'manifest-sha256', 'authorization', 'authorization-sha256', 'serial', 'boot-id', 'hdc', 'out'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--action', choices=['apply', 'rollback'], required=True)
    parser.add_argument('--execute', action='store_true', required=True)
    args = parser.parse_args(argv)
    try:
        manifest, auth, executor, driver = validate(args.manifest, args.manifest_sha256, args.authorization,
            args.authorization_sha256, args.serial, args.boot_id, args.action)
        held = subprocess.run(['bash', auth['_lock_path'], 'held', SERIAL], capture_output=True, text=True, timeout=15)
        need(held.returncode == 0 and not held.stderr and held.stdout.strip() == auth['holder'], 'external lock holder mismatch')
        logs = Path(args.out).parent / (Path(args.out).name + '.transport-' + uuid.uuid4().hex)
        logs.mkdir(parents=True, exist_ok=False)
        dev = Device(executor, driver, args.hdc, logs)
        result = transaction(manifest, dev, args.out, args.action, auth)
        print(json.dumps(result, indent=2)); return result['executor_rc']
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print('REJECT ' + str(exc), file=sys.stderr); return 2


if __name__ == '__main__':
    raise SystemExit(main())
