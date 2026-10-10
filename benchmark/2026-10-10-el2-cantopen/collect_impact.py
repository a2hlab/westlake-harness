#!/usr/bin/env python3
"""PID-scoped observed CANTOPEN and whole-DEX SQLite reference upper bounds."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import zipfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WS = Path(os.environ.get('WORKSPACES', REPO.parent)).resolve()
SOURCE_REPO = WS / 'westlake-harness-tools-inventory'
SOURCE = SOURCE_REPO / 'benchmark/2026-10-10-5cd-demo-regression/resume-organicmaps/compare-observed-89/comparison.json'
MANIFEST = WS / 'westlake-harness/benchmark/2026-10-09-demo-baseline/demo-manifest.json'
SERIAL = '5cd1e3dd00000000000000000923012c'
DEX = re.compile(r'classes(?:\d+)?\.dex\Z')
CALL = re.compile(r'(L[^ ;]+;)\.([^\s:]+):(\([^ ]*\).+?)\s+// method@')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def portable(path):
    path = Path(path)
    return str(path).replace(str(WS) + '/', '$WORKSPACES/').replace(str(Path.home()) + '/', '$HOME/')


def pin(path):
    return dict(path=portable(path), sha256=sha(path))


def expand(path):
    return Path(str(path).replace('$WORKSPACES', str(WS)).replace('$HOME', str(Path.home())))


def compact_events(value):
    if isinstance(value, dict):
        return {key: compact_events(item) for key, item in value.items()
                if not (key == 'text' and 'message' in value and 'line' in value)}
    if isinstance(value, list):
        return [compact_events(item) for item in value]
    return value


def load_fatal():
    path = WS / 'westlake-harness/scripts/lab/first_fatal.py'
    spec = importlib.util.spec_from_file_location('cantopen_existing_first_fatal', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def family(owner, method=None):
    if owner.startswith('Landroidx/room/'):
        return 'Room'
    if owner == 'Landroid/database/sqlite/SQLiteOpenHelper;':
        return 'SQLiteOpenHelper'
    if method == 'openOrCreateDatabase' and owner in ('Landroid/database/sqlite/SQLiteDatabase;', 'Landroid/content/Context;',
                                                       'Landroid/content/ContextWrapper;', 'Landroid/app/Activity;'):
        return 'openOrCreateDatabase'
    return None


def scan_apk(row, dexdump, artifacts):
    apk = expand(row['apk'])
    if sha(apk) != row['apk_sha256']:
        raise ValueError('APK drift: ' + row['key'])
    result = dict(apk=pin(apk), dex=[], calls={name: [] for name in ('Room', 'SQLiteOpenHelper', 'openOrCreateDatabase')},
                  call_counts={name: 0 for name in ('Room', 'SQLiteOpenHelper', 'openOrCreateDatabase')},
                  definition_counts={name: 0 for name in ('Room', 'SQLiteOpenHelper')},
                  definitions={name: [] for name in ('Room', 'SQLiteOpenHelper')})
    output_root = artifacts / row['key']
    output_root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(apk) as archive, tempfile.TemporaryDirectory(prefix='cantopen-dex-') as temporary:
        members = sorted(name for name in archive.namelist() if DEX.fullmatch(name))
        if len(members) != len(set(members)) or not members:
            raise ValueError('missing/duplicate DEX: ' + row['key'])
        for member in members:
            payload = archive.read(member)
            path = Path(temporary) / member
            path.write_bytes(payload)
            raw = output_root / (member + '.stdout.gz')
            error = output_root / (member + '.stderr')
            digest = hashlib.sha256()
            owner = None
            with error.open('wb') as stderr, gzip.open(raw, 'wb') as output:
                process = subprocess.Popen([str(dexdump), '-d', '-n', str(path)], stdout=subprocess.PIPE, stderr=stderr)
                for number, data in enumerate(process.stdout, 1):
                    output.write(data)
                    digest.update(data)
                    text = data.decode('utf-8', errors='backslashreplace').rstrip()
                    if "Class descriptor  : '" in text:
                        owner = text.split("'")[1]
                        label = family(owner)
                        if label in result['definitions']:
                            result['definition_counts'][label] += 1
                            if len(result['definitions'][label]) < 12:
                                result['definitions'][label].append(dict(dex=member, line=number, owner=owner))
                    if 'invoke-' in text and (match := CALL.search(text)):
                        label = family(match[1], match[2])
                        if label:
                            result['call_counts'][label] += 1
                            if len(result['calls'][label]) < 12:
                                result['calls'][label].append(dict(dex=member, line=number, caller=owner,
                                                               target=match[1] + '.' + match[2], text=text.strip()))
                code = process.wait()
            if code:
                raise ValueError('dexdump failed: ' + row['key'] + '/' + member + ' exit=' + str(code))
            result['dex'].append(dict(member=member, version=payload[4:7].decode('ascii'),
                    sha256=hashlib.sha256(payload).hexdigest(), stdout_sha256=digest.hexdigest(), exit=code,
                    raw_stdout=portable(raw), stderr=pin(error)))
    return row['key'], result


def termination(events, pids, existing, fatal):
    candidates = []
    if (existing.get('terminal') or {}).get('event'):
        candidates.append(dict(event=existing['terminal']['event'], root=existing['root'], basis='existing-first_fatal'))
    scoped = [event for event in events if event['pid'] in pids and fatal.classify.is_execution(event)]
    for event in scoped:
        if '[W-ROOM-SURVIVE]' in event['message'] and 'UNCAUGHT in thread' in event['message'] and 'main=true' in event['message']:
            killed = [later for later in scoped if (later['pid'], later['tid']) == (event['pid'], event['tid']) and
                      later['line'] > event['line'] and 0 <= fatal.seconds(later['timestamp']) - fatal.seconds(event['timestamp']) <= 3 and
                      '[W-ROOM-SURVIVE] main-thread fatal -> preserving kill semantics' in later['message']]
            if killed:
                root = fatal.exception_root(scoped, event, 'uncaught-handler')
                candidates.append(dict(event=event, root=root, kill_confirmation=killed[0],
                                       basis='W-ROOM-SURVIVE main=true plus same-PID/TID kill-preservation marker'))
    if not candidates:
        return dict(kind=existing['status'], cantopen=False, evidence=None)
    chosen = min(candidates, key=lambda item: (item['event']['timestamp'], item['event']['line']))
    chain = (chosen.get('root') or {}).get('chain', [])
    bounded = []
    for event in chain:
        if event['line'] > chosen['event']['line'] and (fatal.terminal_kind(event) or
                ('[W-ROOM-SURVIVE]' in event['message'] and 'UNCAUGHT in thread' in event['message'])):
            break
        bounded.append(event)
    linked = [event for event in [chosen['event']] + bounded if 'SQLiteCantOpenDatabaseException' in event['message']]
    if chosen.get('root') and 'chain' in chosen['root']:
        causes = [event for event in bounded if fatal.message(event).startswith('Caused by:')]
        exceptions = [event for event in bounded if fatal.EXCEPTION.search(fatal.message(event)) and not fatal.message(event).startswith('at ')]
        chosen['root'] = dict(chosen['root'], event=(causes or exceptions or [chosen['event']])[-1],
                             chain=bounded[:12] + bounded[12:][-10:], independent_terminal_boundary=True)
    return dict(kind='CANTOPEN' if linked else 'other-or-unresolved-terminal', cantopen=bool(linked), evidence=chosen)


def observed(row, report, fatal):
    path = expand(report['record'])
    if not path.is_absolute():
        path = SOURCE_REPO / path
    path = path.resolve()
    record, events, pids, crashes, disappeared, hashes = fatal.load_run(path.parent)
    if record.get('key') != row['key'] or record.get('package') != row['package'] or record.get('serial') != SERIAL or \
            record.get('apk_sha256') != row['apk_sha256'] or not record.get('finished_at'):
        raise ValueError('measured record identity mismatch: ' + row['key'])
    scoped = [event for event in events if event['pid'] in pids and fatal.classify.is_execution(event)]
    hits = [event for event in scoped if 'SQLiteCantOpenDatabaseException' in event['message']]
    expected_path = '/data/app/el2/100/base/' + row['package'] + '/'
    path_hits = [event for event in hits if expected_path in event['message']]
    existing = fatal.analyze(events, pids, crashes, disappeared) if pids else dict(status='target-pid-unknown', terminal=None, root=None)
    first = termination(events, pids, existing, fatal)
    if first['cantopen'] and not path_hits:
        first.update(kind='CANTOPEN-path-unconfirmed', cantopen=False)
    return dict(record=pin(path), hilog=pin(path.parent / 'hilog.txt'), target_pids=sorted(pids),
                count=len(hits), own_el2_path_hits=len(path_hits), suspect=report.get('semantic', {}).get('class') == 'suspect',
                hits=hits[:12], first_fatal=first, existing_first_fatal=dict(status=existing['status'], terminal=existing['terminal']), diagnostic=hashes)


def build(manifest, comparison, scans, measurements):
    rows = []
    for app in sorted(manifest['apps'], key=lambda item: item['key']):
        if app.get('install') is False:
            continue
        key = app['key']
        measurement = measurements.get(key)
        labels = [label for label, calls in scans[key]['calls'].items() if calls]
        if measurement:
            blocked = 'y' if measurement['first_fatal']['cantopen'] else \
                      'unknown' if measurement['first_fatal']['kind'] in ('process-disappearance-cause-unknown', 'target-pid-unknown') else 'n'
        else:
            blocked = 'possible-static' if labels else 'unknown-no-dex-reference'
        rows.append(dict(key=key, package=app['package'], measured_on_5cd='y' if measurement else 'n',
                    cantopen_count_5cd=measurement['count'] if measurement else '',
                    suspect_5cd=('y' if measurement['suspect'] else 'n') if measurement else 'unmeasured',
                    static_sqlite='|'.join(labels) if labels else 'no-call-reference', predicted_blocked=blocked))
    measured_fatal = [row['key'] for row in rows if row['measured_on_5cd'] == 'y' and row['predicted_blocked'] == 'y']
    predicted = [row['key'] for row in rows if row['predicted_blocked'] == 'possible-static']
    summary = dict(keys=len(rows), measured=len(measurements), unmeasured=len(rows) - len(measurements),
                   measured_cantopen_presence_keys=sum(item['count'] > 0 for item in measurements.values()),
                   measured_suspect_keys=sum(item['suspect'] for item in measurements.values()),
                   measured_suspect_with_cantopen=sum(item['suspect'] and item['count'] > 0 for item in measurements.values()),
                   measured_first_fatal_cantopen_count=len(measured_fatal), measured_first_fatal_cantopen_keys=measured_fatal,
                   predicted_unmeasured_conditional_upper_bound_count=len(predicted), predicted_unmeasured_conditional_keys=predicted,
                   combined_conditional_upper_bound=len(measured_fatal) + len(predicted),
                   unmeasured_startup_first_fatal_proven=0,
                   measured_cantopen_not_confirmed_first_fatal_keys=sorted(key for key, item in measurements.items()
                                if item['count'] > 0 and not item['first_fatal']['cantopen']),
                   static_scanned_keys=len(scans), static_scanned_dex_members=sum(len(item.get('dex', [])) for item in scans.values()),
                   rule='Whole-DEX call references do not prove startup execution. Prediction is conditional; native/dynamic database users can be missed.')
    return rows, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dexdump', type=Path, default=Path.home() / 'Library/Android/sdk/build-tools/37.0.0/dexdump')
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--reuse-static', action='store_true')
    args = parser.parse_args()
    manifest, comparison = read(MANIFEST), read(SOURCE)
    apps = [row for row in manifest['apps'] if row.get('install') is not False]
    measured = {row['key']: row for row in comparison['keys'] if row['category'] != 'missing'}
    if len(apps) != 128 or len(measured) != 89 or len({row['key'] for row in apps}) != 128:
        raise ValueError('expected128/89 scope mismatch')
    fatal = load_fatal()
    measurements = {row['key']: observed(row, measured[row['key']], fatal) for row in apps if row['key'] in measured}
    artifacts = HERE / '.artifacts/dexdump'
    cache = HERE / '.artifacts/static.json'
    if args.reuse_static:
        cached = read(cache)
        if cached['dexdump_sha256'] != sha(args.dexdump) or set(cached['scans']) != {row['key'] for row in apps}:
            raise ValueError('static cache tool/membership drift')
        scans = cached['scans']
        for app in apps:
            if scans[app['key']]['apk']['sha256'] != app['apk_sha256'] or sha(expand(app['apk'])) != app['apk_sha256']:
                raise ValueError('static cache APK drift: ' + app['key'])
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            scans = dict(executor.map(lambda row: scan_apk(row, args.dexdump, artifacts), apps))
        cache.write_text(json.dumps(dict(dexdump_sha256=sha(args.dexdump), scans=scans), sort_keys=True) + '\n')
    for item in scans.values():
        for field in ('calls', 'definitions'):
            item[field] = {kind: samples[:6] for kind, samples in item[field].items()}
    rows, summary = build(manifest, comparison, scans, measurements)
    with (HERE / 'impact.csv').open('w', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    result = dict(schema='el2-cantopen-impact/v1', board_access=False, summary=summary,
                  inputs=dict(manifest=pin(MANIFEST), comparison=pin(SOURCE), dexdump=pin(args.dexdump),
                              first_fatal=pin(WS / 'westlake-harness/scripts/lab/first_fatal.py')),
                  keys={row['key']: dict(static=scans[row['key']], measured=measurements.get(row['key'])) for row in rows})
    (HERE / 'impact-evidence.json').write_text(json.dumps(compact_events(result), separators=(',', ':'), sort_keys=True, ensure_ascii=False) + '\n')
    (HERE / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    with (HERE / 'summary.csv').open('w', newline='') as output:
        fields = ['measured_first_fatal_cantopen_count', 'predicted_unmeasured_conditional_upper_bound_count',
                  'combined_conditional_upper_bound', 'unmeasured_startup_first_fatal_proven']
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerow({field: summary[field] for field in fields})
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
