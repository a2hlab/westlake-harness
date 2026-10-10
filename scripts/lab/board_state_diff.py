#!/usr/bin/env python3
"""Read-only, SHA-verified diff of board snapshots; missing evidence is not equality."""
import argparse
import hashlib
import json
from pathlib import Path
import sys


def coverage_warnings(snapshot):
    return snapshot.get('coverage_warnings', []) + [row for row in snapshot.get('errors', [])
        if row.get('item') == 'deployment-plan' and row.get('reason') ==
        '56-layer target plan not supplied; coverage incomplete']


def collection_usable(snapshot):
    errors = [row for row in snapshot.get('errors', []) if row not in coverage_warnings(snapshot)]
    usable = snapshot.get('collection_complete', snapshot.get('complete') or bool(coverage_warnings(snapshot)))
    return usable is True and not errors and snapshot.get('boot_stable') is True


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
    if not collection_usable(snapshot):
        problems.append(dict(item='snapshot', reason='capture was incomplete/unstable', details=snapshot.get('errors', [])))
    return snapshot, raw, problems


def dictionary_diff(reference, subject):
    absent = {'absent': True}
    return {key: dict(reference=reference.get(key, absent), subject=subject.get(key, absent))
            for key in sorted(set(reference) | set(subject)) if reference.get(key, absent) != subject.get(key, absent)}


def seccomp_observations(reference, subject, changes):
    hints = []
    for section in ['scalars', 'labels', 'params', 'sha', 'raw']:
        for key, delta in changes[section].items():
            relevant = (key == 'selinux_enforce' or key.startswith(('const.cust.', 'param_const_cust_')) or
                        (key.startswith('/system/etc/sandbox/') and key.endswith('.json')) or
                        any(word in key.lower() for word in ['seccomp', 'cfg_layer', 'config_dir_layer', 'follow_x_rules', 'sandbox_label']))
            if relevant:
                hints.append(dict(section=section, key=key, delta=delta, causal_proof=False))
    counts = dict(scope='captured canonical /system paths only; not a whole-tree census', causal_proof=False)
    for name, snapshot in [('reference', reference), ('subject', subject)]:
        labels = snapshot.get('labels', {})
        paths = {label_type: sorted(path for path, label in labels.items()
                                   if (path == '/system' or path.startswith('/system/')) and
                                   label == 'u:object_r:' + label_type + ':s0')
                 for label_type in ['data_local_tmp', 'data_file']}
        counts[name] = {label_type: len(items) for label_type, items in paths.items()}
        counts[name]['paths'] = paths
        counts[name]['captured_system_path_count'] = sum(path == '/system' or path.startswith('/system/') for path in labels)
    if (counts['reference'] != counts['subject'] or
            any(counts[name][label_type] for name in ['reference', 'subject'] for label_type in ['data_local_tmp', 'data_file'])):
        hints.append(dict(section='label-counts', key='system_data_label_counts',
                          delta=dict(reference=counts['reference'], subject=counts['subject']),
                          scope=counts['scope'], causal_proof=False))
    return hints, counts


def compare(reference, subject):
    first, first_raw, first_problems = load(reference)
    second, second_raw, second_problems = load(subject)
    report = dict(schema_version=1, readonly=True, reference=first.get('serial'), subject=second.get('serial'),
                  comparable=not first_problems and not second_problems,
                  incomplete=dict(reference=first_problems, subject=second_problems), diffs={})
    report['coverage_complete'] = first.get('complete') is True and second.get('complete') is True
    report['comparison_scope'] = 'captured-deployment-and-core-fields' if report['coverage_complete'] else 'observed-fields-only'
    report['coverage_warnings'] = dict(reference=coverage_warnings(first), subject=coverage_warnings(second))
    scalars = ['selinux_enforce', 'boot_id', 'uptime', 'config_policy_layer_roots', 'plan_target_count']
    report['diffs']['scalars'] = dictionary_diff({key: first.get(key) for key in scalars}, {key: second.get(key) for key in scalars})
    for field in ['labels', 'params', 'sha', 'pids', 'init_configs']:
        report['diffs'][field] = dictionary_diff(first.get(field, {}), second.get(field, {}))
    report['diffs']['mounts'] = dict(reference=first.get('mounts', []), subject=second.get('mounts', [])) if first.get('mounts') != second.get('mounts') else {}
    first_targets, second_targets = set(first.get('bind_targets', [])), set(second.get('bind_targets', []))
    report['diffs']['bind_targets'] = dict(only_reference=sorted(first_targets - second_targets), only_subject=sorted(second_targets - first_targets))
    report['diffs']['raw'] = dictionary_diff(first_raw, second_raw)
    report['seccomp_relevant_observations'], report['system_data_label_counts'] = seccomp_observations(first, second, report['diffs'])
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
        print('comparison_scope=' + report['comparison_scope'] + ' coverage_complete=' + str(report['coverage_complete']))
        for section, changes in report['diffs'].items():
            print(section + ': ' + json.dumps(changes, sort_keys=True))
        print('seccomp observations are hints, not causal verdicts')
        return 0 if report['comparable'] else 1
    except (ValueError, KeyError, TypeError, OSError) as error:
        print('DIFF-REFUSE: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
