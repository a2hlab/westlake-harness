#!/usr/bin/env python3
"""Offline audit of retained spawn, loader and snapshot evidence; never contacts boards."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


HERE = Path(__file__).resolve().parent
WS = Path(os.environ.get('WORKSPACES', HERE.parents[2])).resolve()
MASTER = WS / 'westlake-harness'
TI = WS / 'westlake-harness-tools-inventory/benchmark'
BAD = WS / 'westlake-harness-t3/benchmark/2026-10-10-5ea-u13-restore-cc'
REVIVE = WS / 'westlake-harness-bms/benchmark/2026-10-10-5ea-revive/.artifacts/attempt-20261010T193711-92111'
SUID = TI / '2026-10-10-5cd-demo-regression/boat-full128/suid-experiment'
GOOD = TI / '2026-10-10-5ea-u13-restore/v2/autonomous-smoke-r2/group-0/20261010T124723-acd1a669/5ea34a4500000000000000001123012c'
BRIDGE = '/system/android/lib64/liboh_adapter_bridge.so'
RUNTIME = '/system/android/lib64/liboh_android_runtime.so'
HOST = '/system/bin/appspawn-x'
LINE = re.compile(r'^\d\d-\d\d\s+\S+\s+(\d+)\s+(\d+)\s+([A-Z])\s+(.+)$')
SPAWN = re.compile(r'WLCGATE:STOCK:SPAWN_RESULT ret=0 pid=(\d+)')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def portable(path):
    path = Path(path).resolve()
    if path.is_relative_to(WS):
        return '$WORKSPACES/' + str(path.relative_to(WS))
    home = Path.home().resolve()
    if path.is_relative_to(home):
        return '$HOME/' + str(path.relative_to(home))
    return str(path)


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + '\n')


def pin(path):
    return dict(path=portable(path), sha256=digest(path))


def analyze(text, observed_pids):
    lines = text.splitlines()
    parsed = [(number, int(match[1]), int(match[2]), match[4], line)
              for number, line in enumerate(lines, 1) if (match := LINE.match(line))]
    spawns = [(number, int(match[1]), pid) for number, pid, tid, message, line in parsed
              if (match := SPAWN.search(message))]
    target_pids = sorted({child for number, child, parent in spawns} | set(observed_pids))
    own = [row for row in parsed if row[1] in target_pids]
    gates = [dict(line=number, pid=pid, text=message[message.index('WLCGATE:'):])
             for number, pid, tid, message, line in own if 'WLCGATE:' in message]
    bridge_errors = [dict(line=number, pid=pid, text=line) for number, pid, tid, message, line in own
                     if BRIDGE in message and 'errno=13' in message]
    exits = [dict(line=number, text=line) for number, pid, tid, message, line in parsed
             if any(re.search(r'\bpid\s+' + str(child) + r'\s+exit with code:\d+', message)
                    for child in target_pids)]
    entry = [int(match[1]) for row in gates
             if (match := re.search(r'PROVIDER:ENTRY_RESULT:(\d+)', row['text']))]
    entry = [value - 2**32 if value >= 2**31 else value for value in entry]
    loader = [int(match[1]) for row in gates
              if (match := re.search(r'LSP:LOAD_ERROR:(\d+)', row['text']))]
    selected = []
    for number, pid, tid, message, line in parsed:
        if (pid in target_pids and any(token in message for token in
                ['WLCGATE:', BRIDGE, '[CHILD_CK]', 'N10b-JNI-OWNER', 'signal: 4'])) or any(row['line'] == number for row in exits) or SPAWN.search(message):
            selected.append(dict(line=number, text=line))
    return dict(target_pids=target_pids, spawns=spawns, observed_pids=observed_pids,
                own_signal4=sum('MUSL-SIGCHAIN' in row[3] and 'signal: 4' in row[3] for row in own),
                all_signal4=sum('MUSL-SIGCHAIN' in row[3] and 'signal: 4' in row[3] for row in parsed),
                bridge_errno13=bridge_errors, loader_errors=loader, provider_entry_results=entry,
                gates=gates, exits=exits, own_java_entry=sum('[CHILD_CK]' in row[3] for row in own),
                selected=selected, has_new_spawn=bool(spawns),
                stage='bridge-load-EACCES' if bridge_errors and loader else
                      'provider-entry' if entry and any(entry) else
                      'java-entry' if any('[CHILD_CK]' in row[3] for row in own) else 'unknown')


def inventory():
    records = [(str(path.relative_to(BAD)), path, 'failed-5ea') for path in sorted(BAD.rglob('record.json'))
               if path.parent.name in ['helloworld', 'zigzag'] and (path.parent / 'hilog.txt').is_file()]
    records += [('revive-' + path.parent.name, path, 'failed-5ea-Boat-retained')
                for path in sorted((REVIVE / 'runner').rglob('record.json'))
                if path.parent.name in ['helloworld', 'zigzag'] and (path.parent / 'hilog.txt').is_file()]
    records += [('healthy-noon-5ea-' + key, GOOD / key / 'record.json', 'outer-lit-control')
                for key in ['helloworld', 'zigzag']]
    for folder, name, status in [('host-suid-r1', '5cd-host-only-suid', 'provider-failure-control'),
                                 ('clean-reboot-r1', 'healthy-5cd-clean-reboot', 'outer-lit-control')]:
        paths = [path for path in sorted((SUID / folder).rglob('record.json'))
                 if path.parent.name == 'helloworld' and (path.parent / 'hilog.txt').is_file()]
        if len(paths) != 1:
            raise ValueError('expected one control record: ' + name)
        records.append((name, paths[0], status))
    return records


def fingerprints(path):
    return {match[2]: match[1] for line in path.read_text().splitlines()
            if (match := re.match(r'^([0-9a-f]{64})\s+(/\S+)', line))}


def mount_rows(text, target):
    rows = []
    for number, line in enumerate(text.splitlines(), 1):
        fields = line.split()
        if len(fields) < 10 or ' - ' not in line:
            continue
        mountpoint = fields[4]
        if target == mountpoint or target.startswith(mountpoint.rstrip('/') + '/'):
            rows.append(dict(line=number, mount_id=fields[0], root=fields[3], target=mountpoint,
                             options=fields[5], original=line))
    if not rows:
        return []
    longest = max(len(row['target']) for row in rows)
    return [row for row in rows if len(row['target']) == longest]


def state_matrix(out, results):
    spec = [
        ('5ea-noon-lit', TI / '2026-10-10-5ea-u13-restore/v2/post-reboot-pre-app/snapshot.json', GOOD / 'runtime-fingerprint.txt', None),
        ('5ea-after-revive-failed-Boat-retained', REVIVE / 'after/snapshot.json', next((REVIVE / 'runner').rglob('runtime-fingerprint.txt')), None),
        ('5ea-definitive-pure-base-failed', None, next((BAD / 'cleanbase-smoke-DEFINITIVE/group-0').rglob('runtime-fingerprint.txt')), None),
        ('5cd-healthy-earlier-boot', Path.home() / 'a2hlab-provision/t2e-inputs/5cd1e3dd00000000000000000923012c/recursive-20261010T134737-66863/snapshot.json',
         next((SUID / 'clean-reboot-r1').rglob('runtime-fingerprint.txt')), None),
        ('61b-seal-pre', WS / 'westlake-harness-wiki/benchmark/2026-10-10-demo-seal-61b/seal-run-20261010T213843/pre/snapshot.json',
         next((TI / '2026-10-09-demo-baseline/t3/plans-v1/window-01/runner/001-cv2-com-kaajjo-libresudoku').rglob('runtime-fingerprint.txt')), None),
        ('5cd-host-only-suid-failed', None, next((SUID / 'host-suid-r1').rglob('runtime-fingerprint.txt')),
         SUID / 'host-suid-r1/007-mountinfo-after.stdout.txt'),
    ]
    rows = []
    snapshots = {}
    for name, snapshot_path, fingerprint_path, external_mount in spec:
        snapshot = json.loads(snapshot_path.read_text()) if snapshot_path else {}
        if snapshot_path:
            snapshots[name] = snapshot_path
        mount_path = external_mount
        if snapshot_path:
            mount_path = snapshot_path.parent / snapshot['items']['init_mountinfo']['raw']
            if digest(mount_path) != snapshot['items']['init_mountinfo']['raw_sha256']:
                raise ValueError('mount raw SHA mismatch')
        mounts = mount_path.read_text() if mount_path else ''
        hashes = fingerprints(fingerprint_path)
        for target in [BRIDGE, RUNTIME, HOST]:
            row = dict(state=name, path=target, sha256=hashes.get(target, 'unknown'),
                       sha_evidence=pin(fingerprint_path), label=snapshot.get('labels', {}).get(target, 'unknown'),
                       snapshot=pin(snapshot_path) if snapshot_path else None,
                       snapshot_boot=snapshot.get('boot_id', 'unknown'), plan_sha256=snapshot.get('plan_sha256'),
                       mounts=mount_rows(mounts, target), mount_evidence=pin(mount_path) if mount_path else None,
                       mount_view='PID1' if mount_path else 'unknown',
                       child_mount_view='unknown', child_label_and_DAC_view='unknown',
                       evidence_join='state observations may differ in boot/time; not a simultaneous child measurement')
            if name == '5cd-host-only-suid-failed' and target == HOST:
                source = SUID / 'host-suid-r1/008-host-stat-after.stdout.txt'
                row['label'] = source.read_text().splitlines()[0].split(':', 3)[3]
                row['mode_owner'] = '0755 0:0'
                row['label_evidence'] = pin(source)
            rows.append(row)
    dump(out / 'file-state-matrix.json', rows)
    with (out / 'file-state-matrix.csv').open('w', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=['state', 'path', 'sha256', 'label', 'snapshot_boot', 'plan_sha256', 'mount_view', 'mount_options', 'mount_target', 'child_mount_view'])
        writer.writeheader()
        for row in rows:
            writer.writerow({**{key: row.get(key) for key in writer.fieldnames if key not in ['mount_options', 'mount_target']},
                             'mount_options': '|'.join(item['options'] for item in row['mounts']),
                             'mount_target': '|'.join(item['target'] for item in row['mounts'])})
    return snapshots


def snapshot_diff(out, snapshots):
    tool = MASTER / 'scripts/lab/board_state_diff.py'
    pairs = [('noon-vs-failed-5ea', snapshots['5ea-noon-lit'], snapshots['5ea-after-revive-failed-Boat-retained']),
             ('5cd-vs-failed-5ea', snapshots['5cd-healthy-earlier-boot'], snapshots['5ea-after-revive-failed-Boat-retained']),
             ('61b-vs-failed-5ea', snapshots['61b-seal-pre'], snapshots['5ea-after-revive-failed-Boat-retained']),
             ('same-plan-5ea-before-after', REVIVE / 'before/snapshot.json', REVIVE / 'after/snapshot.json')]
    reports = []
    raw_root = HERE / '.artifacts/snapshot-diffs'
    raw_root.mkdir(parents=True, exist_ok=True)
    for name, reference, subject in pairs:
        target = raw_root / (name + '.json')
        argv = [sys.executable, str(tool), str(reference), str(subject), '--json', str(target)]
        process = subprocess.run(argv, capture_output=True)
        stdout = raw_root / (name + '.stdout.txt')
        stderr = raw_root / (name + '.stderr.txt')
        stdout.write_bytes(process.stdout)
        stderr.write_bytes(process.stderr)
        report = json.loads(target.read_text())
        reports.append(dict(name=name, argv=[portable(Path(arg)) if Path(arg).is_absolute() else arg for arg in argv],
                            exit=process.returncode, tool=pin(tool), report=pin(target), stdout=pin(stdout), stderr=pin(stderr),
                            reference=pin(reference), subject=pin(subject), plan_sha256=report['plan_sha256'],
                            plan_comparable=report['plan_comparable'], comparable=report['comparable'],
                            incomplete=report['incomplete'], scope=report['comparison_scope'],
                            path_sets=report['diffs']['labels'] if not report['plan_comparable'] else 'same-plan differences retained in raw report'))
    dump(out / 'snapshot-comparison.json', reports)


def run(out):
    out.mkdir(parents=True, exist_ok=True)
    results = []
    evidence = []
    for name, path, status in inventory():
        record = json.loads(path.read_text())
        source = path.parent / 'hilog.txt'
        result = analyze(source.read_text(errors='replace'), [int(pid) for pid in record.get('observed_pids', [])])
        result.update(name=name, status=status, key=path.parent.name, record=pin(path), hilog=pin(source),
                      faultlog_files=[portable(item) for item in sorted(path.parent.rglob('*'))
                                      if item.is_file() and 'faultlogs' in item.parts],
                      package=record.get('package'), boot_id=record.get('boot_id'))
        selected = result.pop('selected')
        evidence.append(dict(name=name, source=pin(source), lines=selected))
        results.append(result)
    dump(out / 'run-analysis.json', results)
    dump(out / 'evidence/hilog-excerpts.json', evidence)
    with (out / 'runs.csv').open('w', newline='') as handle:
        fields = ['name', 'key', 'status', 'target_pids', 'observed_pids', 'has_new_spawn', 'stage', 'own_signal4', 'all_signal4', 'own_java_entry', 'loader_errors', 'provider_entry_results', 'faultlog_count']
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in results:
            writer.writerow({key: len(row['faultlog_files']) if key == 'faultlog_count' else row[key] for key in fields})
    snapshots = state_matrix(out, results)
    snapshot_diff(out, snapshots)
    failed = [row for row in results if row['status'].startswith('failed-5ea')]
    pairs = []
    for key in ['helloworld', 'zigzag']:
        good = next(row for row in results if row['name'] == 'healthy-noon-5ea-' + key)
        bad = next(row for row in results if 'cleanbase-smoke-DEFINITIVE/group-0/' in row['name'] and row['key'] == key)
        good_gates = good['gates']
        bad_gates = bad['gates']
        common = 0
        for first, second in zip(good_gates, bad_gates):
            if first['text'] != second['text']:
                break
            common += 1
        pairs.append(dict(key=key, good=good['hilog'], failed=bad['hilog'], common_gate_prefix=common,
                          first_divergence=dict(good=good_gates[common], failed=bad_gates[common]),
                          earlier_bridge_error=bad['bridge_errno13']))
    dump(out / 'phase-comparison.json', pairs)
    sources = ['mount-delta.json', '003-host-sha-before.stdout.txt', '009-host-sha-after.stdout.txt',
               '005-host-stat-before.stdout.txt', '008-host-stat-after.stdout.txt']
    dump(out / 'evidence/suid-host-delta.json', [dict(source=pin(SUID / 'host-suid-r1' / name),
        text=(SUID / 'host-suid-r1' / name).read_text()) for name in sources])
    hashes = {}
    for name, path in [('5ea-noon', GOOD / 'runtime-fingerprint.txt'),
                       ('5ea-definitive', next((BAD / 'cleanbase-smoke-DEFINITIVE/group-0').rglob('runtime-fingerprint.txt'))),
                       ('5cd-clean-reboot', next((SUID / 'clean-reboot-r1').rglob('runtime-fingerprint.txt'))),
                       ('5cd-suid', next((SUID / 'host-suid-r1').rglob('runtime-fingerprint.txt'))),
                       ('61b-t3', next((TI / '2026-10-09-demo-baseline/t3/plans-v1/window-01/runner/001-cv2-com-kaajjo-libresudoku').rglob('runtime-fingerprint.txt')))]:
        hashes[name] = dict(source=pin(path), paths=fingerprints(path))
    reference = hashes['5ea-definitive']['paths']
    dump(out / 'fingerprint-comparison.json', dict(states=hashes, diffs={name: {
        path: dict(reference=reference.get(path), subject=row['paths'].get(path))
        for path in sorted(set(reference) | set(row['paths'])) if reference.get(path) != row['paths'].get(path)}
        for name, row in hashes.items()}))
    dump(out / 'results.json', dict(readonly=True, board_access=False, vm_access=False, builds=0,
        failed_5ea_records=len(failed), failed_5ea_new_spawn_records=sum(row['has_new_spawn'] for row in failed),
        failed_5ea_bridge_EACCES_records=sum(row['stage'] == 'bridge-load-EACCES' for row in failed),
        failed_5ea_own_signal4=sum(row['own_signal4'] for row in failed),
        failed_5ea_faultlog_files=sum(len(row['faultlog_files']) for row in failed),
        conclusion='Observed 5ea failure is bridge EACCES -> loader 10 -> exit123, not established SIGILL.',
        suid_comparison='5cd provider-entry -2003 is a later distinct failure stage; same mechanism unproved.',
        causal_permission_mechanism='unknown: need contemporaneous child mount/label/DAC/namespace evidence'))
    print(json.dumps(json.loads((out / 'results.json').read_text()), sort_keys=True))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=HERE)
    run(parser.parse_args().out)
