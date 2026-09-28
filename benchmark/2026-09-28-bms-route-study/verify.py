#!/usr/bin/env python3
"""Validate host evidence and honest execution labels, never device success."""
import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def validate(result):
    assert result['board_item'] == 15 and result['supersedes'] == 13
    assert result['device_commands_executed'] == 0
    assert result['r2']['device_deployment'] == 'unverified'
    assert result['r2']['human_review'] == 'pending_review'
    assert not result['validation']['device_success_claim']
    selected = [x for x in result['payload_audit']['archives']
                if x['path'] == result['selected_payload']]
    assert len(selected) == 1
    assert selected[0]['bytes'] == 274575597
    assert selected[0]['sha256'] == 'e30a91993f06fc50ce401655837d9cfdec5a177aca65a311a5810ce14ae71145'
    assert result['pac']['bytes'] == 3514798293
    assert result['pac']['sha256'] == '4046781bfcd033ea62dc339892b671d71a34bad3fa53b6c44d914d79281cb0b8'
    assert len(result['first_hour']) == 5
    for step in result['first_hour']:
        assert step['execution'] == 'unverified' and step['pass'] and step['fallback']
        assert (ROOT / step['commands_in']).is_file()
    assert result['historical_lit_vs_sweep_unlit_intersection'] == []
    assert len(result['historical_apps']) == 5
    assert 'runtime.bcp_copy' in result['host_readiness']['remaining_missing']


def main():
    result = json.loads((ROOT / 'results.json').read_text())
    validate(result)
    # Negative controls ensure accidental old-package selection/false verification fails.
    for mutate in (
        lambda r: r.update(selected_payload='~/t006/t006-baseline-v3.tar.gz'),
        lambda r: r['r2'].update(device_deployment='verified'),
    ):
        bad = copy.deepcopy(result)
        mutate(bad)
        try:
            validate(bad)
        except AssertionError:
            pass
        else:
            raise AssertionError('negative control incorrectly accepted')
    receipt = json.loads((ROOT / 'evidence/cts-ready-materials.json').read_text())
    assert receipt['status'] == 'FAIL' and receipt['exit_code'] == 1
    assert [r['name'] for r in receipt['missing']] == ['runtime.bcp_copy']
    assert len(receipt['unknown']) == 3
    inventory = json.loads((ROOT / 'evidence/source-inventory.json').read_text())
    assert not inventory['invalid_references'] and len(inventory['files']) >= 50
    for source in inventory['files']:
        assert len(source['sha256']) == 64
        for first, last in source['ranges']:
            assert 1 <= first <= last <= source['line_count']
    manifest = json.loads((ROOT / 'evidence/deliverable-hashes.json').read_text())
    for rel, expected in manifest.items():
        path = ROOT / rel
        assert path.is_file(), f'missing evidence: {rel}'
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, f'changed evidence: {rel}'
    print(f'PASS: pinned host receipts, {len(inventory["files"])} source files, '
          f'{len(manifest)} evidence hashes, 2 negative controls; device execution UNVERIFIED')


if __name__ == '__main__':
    main()
