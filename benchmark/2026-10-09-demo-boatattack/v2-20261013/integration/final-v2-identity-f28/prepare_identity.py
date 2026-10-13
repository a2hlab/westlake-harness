#!/usr/bin/env python3
"""Bind one admitted MAIN T4 composition to its original disabled identity/driver.
Local files only; no execute, device transport, deployment or authorization.
"""
import argparse
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
WS = Path(os.environ.get('WORKSPACES', str(HERE.parents[5])))
MAIN = WS / 'westlake-harness'
REL = Path('benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/final-v2-f28')
BOARDS = {'61b0657200000000000000000324012c': '61b',
          '5cd1e3dd00000000000000000923012c': '5cd'}

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result

@contextlib.contextmanager
def local_import(c):
    previous = sys.modules.get('candidate_identity')
    sys.modules['candidate_identity'] = c
    try:
        yield
    finally:
        if previous is None:
            sys.modules.pop('candidate_identity', None)
        else:
            sys.modules['candidate_identity'] = previous

def build(composition, composition_sha, out, install_index=None, index_sha=None, boot_before=None):
    if out.exists():
        raise ValueError('fresh output required')
    doc = json.loads(composition.read_text())
    board = BOARDS[doc['serial']]
    sibling = HERE.parent / ('final-v2-identity-f28-' + board)
    c = load(sibling / 'candidate_identity.py', 'f28_identity_' + board)
    c.need(c.sha(composition) == composition_sha, 'independent composition full SHA differs')
    producer_path = MAIN / REL / 'selfcheck/compile_selfcheck.py'
    c.need(doc['compiler'] == c.pin(producer_path) and c.sha(producer_path) == c.SELFCHECK_COMPILER_SHA,
           'MAIN exact producer required; no worktree example')
    producer = c.module(producer_path, 'f28_main_composition')
    _, _, admitted = producer.verified(composition)
    request_path = producer.pin(admitted['request'], composition.parent)
    q = producer.read(request_path)
    root = MAIN / REL / ('board' + board)
    request = dict(serial=c.SERIAL, placement_plan=q['placement_plan'],
                   provider_freeze=q['provider_freeze'], planned_selfcheck=admitted['planned_selfcheck'],
                   v1_seal=q['v1_seal'], baseline_smoke=c.pin(c.BASE_SMOKE),
                   selfcheck_composition=c.pin(composition), base_source=q['base'], execution_enabled=False,
                   programs={name: c.pin(root / 'provider' / file) for name, file in {
                       'provider_executor': 'installer.py', 'provider_contract': 'candidate_contract.py',
                       'provider_compiler': 'prepare.py', 'boat_identity': 'boat_identity.py'}.items()})
    request['programs']['selfcheck_compiler'] = c.pin(producer_path)
    c.need(bool(install_index) == bool(index_sha) == bool(boot_before),
           'same-board index/full SHA and actual pre-reboot boot must be supplied together')
    if install_index:
        c.pinned({'path': str(install_index), 'sha256': index_sha})
    with local_import(c):
        compiler = load(sibling / 'compile_candidate.py', 'f28_local_compiler_' + board)
        proof = compiler.build(request, out / 'identity')
        (out / 'request.bound.disabled.json').write_text(json.dumps(request, indent=2) + '\n')
        if install_index:
            driver = load(sibling / 'run_candidate_post_reboot.py', 'f28_original_driver_' + board)
            driver.prepare(c.MANIFEST, c.TIERS, install_index, out / 'round', boot_before,
                           out / 'identity/smoke.json', serial=c.SERIAL,
                           candidate_proof=out / 'identity/candidate-proof.json',
                           candidate_sha=c.sha(out / 'identity/candidate-proof.json'))
    status = dict(status='EXPECTED954_NOT_OBSERVED_DISABLED', serial=c.SERIAL, device_calls=0,
                  proof=c.pin(out / 'identity/candidate-proof.json'), generation=proof['generation_sha256'],
                  sha_objects=len(proof['expected']), file_metadata=len(proof['presence_metadata']),
                  directories=len(proof['directory_metadata']), composition=c.pin(composition),
                  round_status='PREPARED_DISABLED' if install_index else 'PENDING_SAME_BOARD_INSTALLED_RECORDS_AND_REBOOT_ORIGIN',
                  pending=['new deployment/boot', 'full954 live-readonly', 'fresh128'] +
                          (['user unseal'] if board == '61b' else []) + ['outer signoff'])
    (out / 'result.json').write_text(json.dumps(status, indent=2) + '\n')
    return status

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--composition', type=Path, required=True)
    p.add_argument('--composition-sha256', required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--install-index', type=Path)
    p.add_argument('--install-index-sha256')
    p.add_argument('--boot-before')
    a = p.parse_args()
    try:
        result = build(a.composition, a.composition_sha256, a.out, a.install_index,
                       a.install_index_sha256, a.boot_before)
    except (ValueError, KeyError, TypeError, OSError) as error:
        print('REFUSED: ' + str(error), file=sys.stderr)
        return 2
    print(json.dumps(result))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
