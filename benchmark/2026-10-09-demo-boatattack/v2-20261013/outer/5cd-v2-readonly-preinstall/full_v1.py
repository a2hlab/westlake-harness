"""Read the complete original 5cd R5 inventory; no device writes or user-content reads."""
import hashlib
import json
import re
import shlex
import subprocess
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
SERIAL = '5cd1e3dd00000000000000000923012c'
HDC = '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
SOURCE = ROOT / 'benchmark/2026-10-12-v1-seal-execution/seal-final-20261013/selfcheck-5cd-r5.json'
OUT = HERE / 'full-v1'
OUT.mkdir(exist_ok=False)


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def read(name, command):
    marker = '__READONLY_' + uuid.uuid4().hex + '__'
    wrapped = '/system/bin/sh -c ' + shlex.quote(command) + '; read_rc=$?; printf "\\n' + marker + '%s\\n" "$read_rc"'
    argv = [HDC, '-t', SERIAL, 'shell', wrapped]
    started = time.time()
    result = subprocess.run(argv, capture_output=True, timeout=180)
    (OUT / (name + '.stdout.txt')).write_bytes(result.stdout)
    (OUT / (name + '.stderr.txt')).write_bytes(result.stderr)
    save(OUT / (name + '.json'), dict(argv=argv, rc=result.returncode,
                                     started=started, finished=time.time()))
    text = result.stdout.decode()
    match = re.search(r'\n' + marker + r'([0-9]+)\s*$', text)
    if result.returncode or result.stderr.strip() or not match or match[1] != '0':
        raise ValueError('read failed: ' + name)
    return text[:match.start()].strip()


source = json.loads(SOURCE.read_text())
assert source['serial'] == SERIAL and source['status'] == 'PASS'
expected = {row['target']: row['expected'] for row in source['checks']}
assert len(expected) == len(source['checks']) == 940
boot_before = read('boot-before', 'cat /proc/sys/kernel/random/boot_id')
actual, metadata = {}, {}
paths = sorted(expected)
for start in range(0, len(paths), 32):
    selected = paths[start:start + 32]
    command = ('set -eu; for p in ' + ' '.join(map(shlex.quote, selected)) +
               '; do test -f "$p"; test ! -L "$p"; printf "TARGET=%s\\n" "$p"; '
               'sha256sum "$p"; stat -c "%a:%u:%g" "$p"; ls -Zd "$p"; done')
    parts = read('files-%03d' % start, command).split('TARGET=')[1:]
    assert len(parts) == len(selected)
    for target, part in zip(selected, parts):
        lines = part.strip().splitlines()
        assert len(lines) == 4 and lines[0] == target
        digest, name = lines[1].split(None, 1)
        assert name == target and re.fullmatch('[a-f0-9]{64}', digest)
        mode, uid, gid = lines[2].split(':')
        label, name = lines[3].split(None, 1)
        assert name == target and re.fullmatch('u:object_r:[A-Za-z0-9_]+:s0', label)
        actual[target] = digest
        metadata[target] = dict(mode=mode, uid=int(uid), gid=int(gid), label=label)
    print('read', len(actual), flush=True)
boot_after = read('boot-after', 'cat /proc/sys/kernel/random/boot_id')
assert boot_before == boot_after
diff = {p: dict(expected=expected[p], actual=actual[p]) for p in paths if expected[p] != actual[p]}
save(OUT / 'result.json', dict(status='READONLY_HASH_INVENTORY_COMPLETE', serial=SERIAL,
     boot_before=boot_before, boot_after=boot_after, expected=expected, actual=actual,
     metadata=metadata, differences=diff, device_writes=0,
     source=dict(path=str(SOURCE.relative_to(ROOT)), sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest()),
     scope='940 original R5 file hashes and metadata only; not an execution of full R5 nonfile/host checks'))
print(json.dumps(dict(targets=len(actual), differences=len(diff), boot=boot_after, device_writes=0)))
