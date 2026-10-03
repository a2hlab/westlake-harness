import difflib
import hashlib
import json
from pathlib import Path

GATE_TARGETS = {'knowledge/gates/native-predeploy-exceptions.json', 'knowledge/gates/image-provenance-exceptions.json'}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()


def patch_bytes(before, after, target):
    return ''.join(difflib.unified_diff(before.decode().splitlines(keepends=True), after.decode().splitlines(keepends=True),
        fromfile='a/' + target, tofile='b/' + target)).encode()


def append_rows(before, rows):
    data = json.loads(before)
    existing = data['exceptions']
    def identity(row):
        return tuple(row.get(key) for key in ['gate', 'package_manifest_sha256', 'inputs_sha256', 'issue_id']) if 'gate' in row else row['id']
    seen = {identity(row) for row in existing}
    for row in rows:
        key = identity(row)
        if key in seen:
            raise ValueError('Duplicate or already-applied exception: ' + str(key))
        seen.add(key)
    data['exceptions'] = existing + rows
    return encoded(data)


def prepared_bytes(change, before, here):
    if change['kind'] == 'append-exceptions':
        if change['target'] not in GATE_TARGETS:
            raise ValueError('Unexpected gate target')
        if before is None or digest(before) != change['before_sha256']:
            raise ValueError('Target preimage SHA mismatch: ' + change['target'])
        rows_path = here / change['rows']
        if digest(rows_path.read_bytes()) != change['rows_sha256']:
            raise ValueError('Prepared row digest mismatch')
        result = append_rows(before, json.loads(rows_path.read_text()))
        patch = patch_bytes(before, result, change['target'])
    elif change['kind'] == 'derive-static-policy':
        expected_prefix = 'benchmark/2026-10-03-u15-u16-gate-batch/.artifacts/applied-static/'
        if not change['target'].startswith(expected_prefix) or '..' in Path(change['target']).parts:
            raise ValueError('Static output cannot target an authorized bundle')
        if before is not None:
            raise ValueError('Derived policy target already exists')
        source = here / change['preimage_snapshot']
        if digest(source.read_bytes()) != change['preimage_snapshot_sha256']:
            raise ValueError('Policy preimage snapshot drift')
        result = (here / change['candidate_snapshot']).read_bytes()
        patch = patch_bytes(source.read_bytes(), result, change['original_policy_name'])
    else:
        raise ValueError('Unknown change kind')
    if digest(result) != change['after_sha256']:
        raise ValueError('Target postimage SHA mismatch')
    if (here / change['patch']).read_bytes() != patch or digest(patch) != change['patch_sha256']:
        raise ValueError('Exact unified patch mismatch')
    return result
