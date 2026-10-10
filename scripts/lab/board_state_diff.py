#!/usr/bin/env python3
"""Read-only, SHA-verified diff of board snapshots; missing evidence is not equality."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def load(path):
    path = Path(path)
    if path.is_dir():
        path = path / 'snapshot.json'
    snapshot = json.loads(path.read_text())
    problems = []
    raw = {}
    for name, item in snapshot.get('items', {}).items():
        blobs = []
        for filename, pin in [('raw', 'raw_sha256'), ('stderr_raw', 'stderr_sha256')]:
            relative = item.get(filename)
            source = path.parent / (relative or '')
            if not relative or source.is_symlink() or not source.resolve().is_relative_to(path.parent.resolve()) or not source.is_file():
                problems.append(dict(item=name, reason='missing/unsafe raw evidence: ' + filename))
                continue
            blob = source.read_bytes()
            if hashlib.sha256(blob).hexdigest() != item.get(pin):
                problems.append(dict(item=name, reason='raw SHA mismatch: ' + filename))
                continue
            blobs.append(blob.decode('utf-8', errors='backslashreplace'))
        if len(blobs) == 2:
            raw[name] = dict(stdout=blobs[0], stderr=blobs[1], rc=item['rc'])
    if not snapshot.get('complete') or not snapshot.get('boot_stable'):
        problems.append(dict(item='snapshot', reason='capture was incomplete/unstable', details=snapshot.get('errors', [])))
    return snapshot, raw, problems


def dictionary_diff(reference, subject):
    absent = {'absent': True}
    return {key: dict(reference=reference.get(key, absent), subject=subject.get(key, absent))
            for key in sorted(set(reference) | set(subject)) if reference.get(key, absent) != subject.get(key, absent)}


def compare(reference, subject):
    first, first_raw, first_problems = load(reference)
    second, second_raw, second_problems = load(subject)
    report = dict(schema_version=1, readonly=True, reference=first.get('serial'), subject=second.get('serial'),
                  comparable=not first_problems and not second_problems,
                  incomplete=dict(reference=first_problems, subject=second_problems), diffs={})
    scalars = ['selinux_enforce', 'boot_id', 'uptime', 'config_policy_layer_roots', 'plan_target_count']
    report['diffs']['scalars'] = dictionary_diff({key: first.get(key) for key in scalars}, {key: second.get(key) for key in scalars})
    for field in ['labels', 'params', 'sha', 'pids', 'init_configs']:
        report['diffs'][field] = dictionary_diff(first.get(field, {}), second.get(field, {}))
    report['diffs']['mounts'] = dict(reference=first.get('mounts', []), subject=second.get('mounts', [])) if first.get('mounts') != second.get('mounts') else {}
    first_targets, second_targets = set(first.get('bind_targets', [])), set(second.get('bind_targets', []))
    report['diffs']['bind_targets'] = dict(only_reference=sorted(first_targets - second_targets), only_subject=sorted(second_targets - first_targets))
    report['diffs']['raw'] = dictionary_diff(first_raw, second_raw)
    hints = []
    for section in ['scalars', 'labels', 'params', 'sha', 'raw']:
        for key, delta in report['diffs'][section].items():
            if key == 'selinux_enforce' or any(word in key.lower() for word in ['seccomp', 'cfg_layer', 'config_dir_layer', 'follow_x_rules']):
                hints.append(dict(section=section, key=key, delta=delta, causal_proof=False))
    report['seccomp_relevant_observations'] = hints
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('subject', type=Path)
    parser.add_argument('--json', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = compare(args.reference, args.subject)
        args.json.write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
        print('COMPARABLE' if report['comparable'] else 'INCOMPARABLE: missing/drifted/incomplete evidence')
        for section, changes in report['diffs'].items():
            print(section + ': ' + json.dumps(changes, sort_keys=True))
        print('seccomp observations are hints, not causal verdicts')
        return 0 if report['comparable'] else 1
    except (ValueError, KeyError, TypeError, OSError) as error:
        print('DIFF-REFUSE: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
