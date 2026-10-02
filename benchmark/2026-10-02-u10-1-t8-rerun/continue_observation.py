"""Build a fresh Stage A continuation offline; never rebuild or arm the candidate.

A terminal record is evidence of testing, not screenshot signoff. Interrupted and
missing records remain pending. Failed cleanup must be recovered before resuming.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path

H = Path(__file__).resolve().parent
TERMINAL = {'captured', 'foreground_unconfirmed', 'capture_rejected',
            'app_failed', 'sandbox_prep_failed'}


def read(path):
    return json.loads(path.read_text())


def expand(value):
    return Path(os.path.expanduser(os.path.expandvars(value)))


def keys_of(plan):
    return [k for shard in plan['shards'] for k in expand(shard['keys_file']).read_text().split()]


def measured(plan, roots):
    """Only accept complete cleanup, same-SHA/serial receipts and candidate fingerprints."""
    assert plan['phase'] == 'A'
    done = set()
    for root in roots:
        receipt = read(root / 'window-input.json')
        for field in ['serial', 'bundle_sha256', 'package_manifest_sha256', 'phase']:
            assert receipt[field] == plan[field], 'continuation receipt mismatch: ' + field
        runner = read(root / 'runner/board-run-result.json')
        assert runner.get('before_unlock') == 0, 'prior finish failed; recover U9 before continuation'
        restored = read(root / 'observation-restored.json')
        assert restored.get('passed') is True and restored.get('serial') == plan['serial'], 'U9 restoration receipt required'
        # Restrict search to batch shards: smoke controls must never consume assigned keys.
        for shard in receipt['plan']['shards']:
            assigned = set(receipt['assigned_shards'][shard['name']])
            for record in (root / 'runner' / shard['name']).rglob('record.json'):
                row = read(record)
                if row.get('key') not in assigned or row.get('serial') != plan['serial']:
                    continue
                if row.get('status') not in TERMINAL or not row.get('finished_at'):
                    continue
                for kind, filename in [('runtime', 'runtime-fingerprint.txt'), ('boot', 'boot-image-fingerprint.txt')]:
                    fp = record.parent.parent / filename
                    assert fp.is_file(), 'batch fingerprint evidence absent: ' + str(fp)
                    digest = hashlib.sha256(fp.read_text().strip().encode()).hexdigest()[:12]
                    assert digest == receipt['expected_fingerprints'][kind]['sha256_12'], 'candidate fingerprint mismatch'
                done.add(row['key'])
    assert done <= set(keys_of(plan)), 'prior window contains keys outside this board assignment'
    return done


def prepare(plan, roots, output, run_root):
    done = measured(plan, roots)
    assert not output.exists(), 'fresh continuation plan directory required'
    assert not run_root.exists(), 'fresh transaction/run output required'
    remaining = [k for k in keys_of(plan) if k not in done]
    assert remaining, 'no unmeasured keys remain; send complete results to outer review'
    output.mkdir(parents=True)
    result = copy.deepcopy(plan)
    result['shards'] = []
    for shard in plan['shards']:
        keys = [k for k in expand(shard['keys_file']).read_text().split() if k not in done]
        if not keys:
            continue
        file = output / (shard['name'] + '.txt')
        file.write_text('\n'.join(keys) + '\n')
        result['shards'].append(dict(shard, keys_file=str(file)))
    result['out'] = str(run_root / 'runner')
    for field in ['after_lock', 'before_unlock']:
        argv = result[field]
        argv[argv.index('--root') + 1] = str(run_root)
    target = output / 'plan.json'
    result['after_lock'][result['after_lock'].index('--plan') + 1] = str(target)
    result['execution_enabled'] = False
    result['approval'] = 'Continuation REVIEW ONLY: outer approval required, same bundle bytes/SHA'
    result['resume_evidence'] = [str(root) for root in roots]
    target.write_text(json.dumps(result, indent=2) + '\n')
    (output / 'remaining.json').write_text(json.dumps({'measured': sorted(done), 'unmeasured': remaining,
        'interpretation': 'tested records only; no lit verdict inferred',
        'bundle_sha256': plan['bundle_sha256']}, indent=2) + '\n')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('plan', type=Path)
    parser.add_argument('--prior-root', type=Path, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--run-root', type=Path, required=True)
    args = parser.parse_args()
    print(prepare(read(args.plan), args.prior_root, args.output.resolve(), args.run_root.resolve()))
