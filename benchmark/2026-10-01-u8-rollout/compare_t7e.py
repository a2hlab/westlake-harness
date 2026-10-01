"""Evidence comparison for the proposed T7e boot.art-only exception.

This produces evidence, never authorizes deployment or changes a gate.
"""
import argparse
import hashlib
import json
from pathlib import Path

BACKTRACE = range(0x3e3b8, 0x3e3c0)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def compare(reference, replay, expected, command):
    rows = {}
    for name, digest in sorted(expected.items()):
        old = (reference / name).read_bytes()
        new = (replay / name).read_bytes()
        changed = [i for i, (a, b) in enumerate(zip(old, new)) if a != b]
        allowed = (name == 'boot.art' and len(old) == len(new)
                   and all(i in BACKTRACE for i in changed))
        rows[name] = {
            'reference_sha256': sha(old), 'replay_sha256': sha(new),
            'reference_matches_staging': sha(old) == digest,
            'equal': old == new, 'reference_bytes': len(old), 'replay_bytes': len(new),
            'different_bytes': len(changed) + abs(len(old) - len(new)),
            'changed_offsets': changed if name == 'boot.art' else changed[:32],
            'within_proposed_exception': allowed,
        }
    # Complete original command bytes must occur in both oat headers.
    needle = command.encode()
    command_same = all(needle in (root / 'boot.oat').read_bytes()[:20000]
                       for root in (reference, replay))
    equal_count = sum(r['equal'] for r in rows.values())
    exception_only = (len(rows) == 27 and equal_count == 26
                      and not rows['boot.art']['equal']
                      and rows['boot.art']['within_proposed_exception']
                      and rows['boot.oat']['equal'] and command_same
                      and all(r['reference_matches_staging'] for r in rows.values()))
    return {'classification': 'candidate-for-outer-approval' if exception_only else 'refused',
            'equal_files': equal_count, 'total_files': len(rows),
            'exact_embedded_command_in_both': command_same,
            'boot_art_only_proposal_satisfied': exception_only,
            'files': rows, 'device_io': False}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--reference', type=Path, required=True)
    p.add_argument('--replay', type=Path, required=True)
    p.add_argument('--proposal', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    proposal = json.loads(a.proposal.read_text())
    result = compare(a.reference, a.replay, proposal['outputs'], proposal['build_command'])
    a.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'files'}))
    raise SystemExit(0 if result['boot_art_only_proposal_satisfied'] else 1)
