"""Positive target-PID BitVector evidence and independent first-fatal correlation."""

import argparse
from collections import Counter
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT/'scripts/lab'))
import first_fatal

STATE = {'RUNTIME':'e953c0921536', 'BOOTIMAGE':'4db882a81732'}
PREDICTION = ROOT/'benchmark/2026-10-01-b10-theme-graphics/PREDICTIONS.csv'
PREDICTION_SHA = 'c115d17cd826c479c2f549b2b9e0e92825a4029cab1383079fe601276add12bd'


def sha(payload):
    return hashlib.sha256(payload).hexdigest()


def frozen():
    payload = PREDICTION.read_bytes()
    if sha(payload) != PREDICTION_SHA:
        raise ValueError('166-key identity CSV drift')
    rows = list(csv.DictReader(io.StringIO(payload.decode())))
    output = {row['key']:row for row in rows}
    if len(rows) != 166 or len(output) != 166:
        raise ValueError('Incomplete frozen 166-key identity')
    return output


def extract(events, pids):
    positive = []
    zero = []
    foreign = 0
    malformed = []
    for event in events:
        text = event['message']
        if '[IFACE-RAW]' not in text and '[IFACE-BITS]' not in text:
            continue
        bits = re.search(r'\bgarbageSetBits\s*=\s*(\d+)\b', text)
        if not bits:
            continue
        if event['pid'] not in pids:
            foreign += 1
            continue
        klass = re.search(r'\bklass=(\S+)', text)
        entry = dict(class_name=klass[1] if klass else None, garbage_set_bits=int(bits[1]), event=event)
        if entry['garbage_set_bits'] > 0:
            positive.append(entry)
            if klass is None:
                malformed.append(entry)
        else:
            zero.append(entry)
    return dict(positive=positive, zero=zero, foreign_pid_lines_excluded=foreign, unknown_class_positive=malformed)


def correlate(bits, fatal):
    if not bits['positive']:
        return dict(status='no-positive-observed-not-proof-clean', causal=False, before_first_terminal=[])
    terminal = (fatal.get('terminal') or {}).get('event')
    if terminal is None:
        return dict(status='positive-exposure-without-observed-terminal' if fatal['status']=='no-observed-termination' else 'positive-exposure-terminal-order-unknown', causal=False, before_first_terminal=[])
    before = [entry for entry in bits['positive'] if entry['event']['pid']==terminal['pid'] and
              (entry['event']['timestamp'], entry['event']['line']) <= (terminal['timestamp'], terminal['line'])]
    if not before:
        return dict(status='positive-only-after-or-other-PID-than-first-terminal', causal=False, before_first_terminal=[])
    root = fatal.get('root') or {}
    text = '\n'.join(event.get('message', event.get('text', '')) for event in [root.get('event') or {}, *root.get('chain', []), *root.get('frames', [])])
    linked = [entry for entry in before if entry['class_name'] and entry['class_name'].removeprefix('L').removesuffix(';').replace('/', '.') in text]
    return dict(status='suspected-class-linked-to-first-fatal' if linked else 'suspected-positive-before-first-fatal-unlinked', causal=False,
        before_first_terminal=before, class_linked_evidence=linked,
        limitation='Positive bits and temporal/class co-occurrence are not proof of the fatal cause; require libart fix replay or verified slot/method evidence')


def admit(roots, expected, full=True):
    selected = {}
    pieces = []
    missing_roots = []
    for root in roots:
        if not root.is_dir():
            missing_roots.append(root.name)
            continue
        if list(root.rglob('INVALID*')) or 'seq-' not in root.name:
            raise ValueError('Invalid/non-sequential U8 run root')
        plans = list(root.rglob('plan.json'))
        if not plans:
            missing_roots.append(root.name)
            continue
        for plan_path in sorted(plans):
            folder = plan_path.parent
            plan = json.loads(plan_path.read_text())
            planned = {row['key']:row for row in plan['apps']}
            facts_path = next((parent/'facts.txt' for parent in [folder,*folder.parents[:4]] if (parent/'facts.txt').is_file()), None)
            if facts_path is None:
                raise ValueError('Missing U8 facts')
            facts = facts_path.read_text(errors='replace')
            if any(not re.search(field+r' fingerprint='+pin+r'\b', facts) for field,pin in STATE.items()):
                raise ValueError('Wrong U8 runtime/image facts')
            record_paths = sorted(folder.rglob('record.json'))
            piece_keys = []
            for path in record_paths:
                record = json.loads(path.read_text())
                key = record['key']
                if key not in planned or key not in expected:
                    raise ValueError('Unplanned/unknown U8 key')
                if key in selected:
                    raise ValueError('Duplicate U8 attempts; explicitly select signed attempt roots')
                if any(record.get(field) != expected[key][field] for field in ['package','apk_sha256']):
                    raise ValueError('U8 record APK/package mismatch')
                completed_probe = (record.get('diagnostics') or {}).get('complete') is True and any(shot.get('captured') and shot.get('scheduled_seconds')==20 for shot in record.get('screenshots',[]))
                if record.get('status')=='refused' or (record.get('status')=='batch_interrupted' and not completed_probe):
                    if full:
                        raise ValueError('Incomplete/refused U8 app attempt')
                    continue
                selected[key] = path
                piece_keys.append(key)
            pieces.append(dict(root=root.name, run_folder=folder.name, planned_keys=len(planned), recorded_keys=len(piece_keys),
                plan_sha256=sha(plan_path.read_bytes()), facts_sha256=sha(facts_path.read_bytes()), keys=sorted(piece_keys)))
    if full and (missing_roots or set(selected) != set(expected)):
        raise ValueError('U8 full sweep incomplete; final BitVector impact is pending')
    return selected, dict(pieces=pieces, missing_roots=missing_roots, unobserved_keys=sorted(set(expected)-set(selected)), full=full)


def analyze_run(path, source_root):
    record = json.loads(path.read_text())
    folder = path.parent
    source = str(folder.relative_to(source_root))
    if not (folder/'hilog.txt').is_file():
        return dict(key=record['key'], source=source, record_sha256=sha(path.read_bytes()), probe_status=record.get('status'), status='missing-hilog-unverified', bits=None,
                    fatal=None, correlation=dict(status='unknown-no-log', causal=False))
    record, events, pids, reports, disappeared, binding = first_fatal.load_run(folder)
    fatal = first_fatal.analyze(events, pids, reports, disappeared)
    bits = extract(events, pids)
    return dict(key=record['key'], package=record['package'], apk_sha256=record['apk_sha256'], source=source, binding=binding, probe_status=record.get('status'),
        status='target-PID-bound' if pids else 'no-target-PID-unverified', target_pids=sorted(pids), bits=bits, fatal=fatal, correlation=correlate(bits, fatal))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspaces', type=Path, default=Path(os.environ.get('WORKSPACES', ROOT.parent)))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--partial', action='store_true')
    parser.add_argument('--run-root', type=Path, action='append')
    args = parser.parse_args()
    sweep = args.workspaces/'westlake-harness-t4/benchmark/2026-10-01-u8-sweep'
    roots = args.run_root or [sweep/(board+'-seq-'+cohort) for board in ['5ea','5cd','61b'] for cohort in ['v1','cv2']] + [sweep/'5cd-seq-v1-rest']
    try:
        selected, coverage = admit(roots, frozen(), not args.partial)
        rows = []
        for key, path in sorted(selected.items()):
            rows.append(analyze_run(path, args.workspaces))
            print('BITVECTOR', key, rows[-1]['correlation']['status'], flush=True)
        output = dict(schema='b10-libart-bitvector-v1', mode='partial-unverified-not-final' if args.partial else 'completed-sequential-U8', coverage=coverage, rows=rows,
            counts=dict(Counter(row['correlation']['status'] for row in rows)),
            dependencies={str(path.relative_to(ROOT)):sha(path.read_bytes()) for path in [Path(__file__), Path(first_fatal.__file__)]},
            selected_roots=[str(root.relative_to(args.workspaces)) for root in roots],
            admission_rule='Outer selected six seq pieces plus 5cd-seq-v1-rest; complete t20+diagnostic receipts remain usable if later cleanup failed, incomplete interrupted probes do not',
            state=STATE, input_identity_csv_sha256=PREDICTION_SHA, limitation='No static or log-only causal verdict; zero bits, missing logs and no terminal are not victims')
        args.output.write_text(json.dumps(output,sort_keys=True)+'\n')
        return 0
    except (OSError, ValueError, KeyError) as error:
        print('BITVECTOR REFUSED: '+str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
