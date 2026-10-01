#!/usr/bin/env python3
"""Join the call-site request scan with what our runtime provides, and with how AOSP 14 builds each manager.

    gap_table.py [--provided provided-services.csv]
reads service-summary.csv + requested-services.csv (scan_service_calls.py) and cc-wiki's provided-services.csv
(our-source inventory), writes gap-table.csv. Columns:
  fetch = how AOSP 14 SystemServiceRegistry builds the manager:
          binder  - the fetcher calls ServiceManager.getService*/getServiceOrThrow; with no binder the fetcher
                    throws ServiceNotFoundException and getSystemService returns null to the app
          client  - the fetcher builds the manager in-process (LayoutInflater, SystemVibrator, ...); a missing
                    binder can only bite later, inside a manager method
          module  - not registered in SystemServiceRegistry.java; an apex FrameworkInitializer registers it
                    (connectivity, phone, wifi, bluetooth, ...), so whether route-A has a fetcher at all is a
                    separate question
  provided = cc-wiki's status for the name (real-oh / compat-floor / local-binder / local-stub / registry-stub /
             explicit-null), or '-' when our runtime does not provide it.
Rows sort: not provided + binder/module first, then by keys that are not lit.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'scripts/lab'))
import lab_paths  # noqa: E402

AOSP = lab_paths.inputs() / 'aosp-14.0.0_r1-src/frameworks/base/core/java/android'


def fetch_kinds():
    consts = dict(re.findall(r'public static final String ([A-Z0-9_]+_SERVICE)\s*=\s*"([^"]+)"',
                             (AOSP / 'content/Context.java').read_text()))
    src = (AOSP / 'app/SystemServiceRegistry.java').read_text()
    kinds = {}
    chunks = re.split(r'(?=registerService\(\s*Context\.)', src)
    for chunk in chunks[1:]:
        m = re.match(r'registerService\(\s*Context\.([A-Z0-9_]+)', chunk)
        name = consts.get(m.group(1))
        if not name:
            continue
        binder = re.search(r'ServiceManager\.getService(OrThrow)?\(', chunk)   # chunk = this fetcher only
        kinds[name] = 'binder' if binder else kinds.get(name, 'client')
    return kinds


def provided_map(path):
    out = {}
    for row in csv.DictReader(open(path)):
        for name in re.split(r'[^a-z_]+', row['service'].lower()):
            if name:
                out[name] = row['status']
    return out


def not_published(root):
    """service -> U9 keys whose hilog has SystemServiceRegistry's 'No service published for: <service>'."""
    out = {}
    for f in root.rglob('hilog.txt'):
        for name in set(re.findall(r'No service published for: ?([A-Za-z_.]+)', f.read_text(errors='replace'))):
            out.setdefault(name, set()).add(f.parent.name)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--provided', default=str(HERE / 'provided-services.csv'))
    ap.add_argument('--hilog-root', default=str(lab_paths.workspaces() / 'westlake-harness-u7-executor/benchmark/'
                                                '2026-10-01-u9-native/rollout/approved-j10g'),
                    help='U9 signed sweep runs (key/hilog.txt below it)')
    args = ap.parse_args()
    kinds = fetch_kinds()
    provided = provided_map(args.provided)
    unpublished = not_published(Path(args.hilog_root))
    rows = []
    for r in csv.DictReader(open(HERE / 'service-summary.csv')):
        svc = r['service']
        rows.append({'service': svc, 'keys': int(r['keys']), 'lit': int(r['lit']), 'not_lit': int(r['not_lit']),
                     'call_sites': int(r['call_sites']), 'fetch': kinds.get(svc, 'module'),
                     'provided': provided.get(svc, '-'),
                     'u9_not_published_keys': len(unpublished.get(svc, ()))})
    gap = lambda x: x['provided'] in ('-', 'explicit-null') and x['fetch'] != 'client'
    rows.sort(key=lambda x: (not gap(x), -x['not_lit'], -x['keys'], x['service']))
    with open(HERE / 'gap-table.csv', 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]) + ['gap'])
        w.writeheader()
        for x in rows:
            w.writerow(dict(x, gap='yes' if gap(x) else 'no'))
    print(f'{len(rows)} requested services; {sum(map(gap, rows))} gaps (not provided, fetched through a binder '
          f'or an apex module); {sum(1 for x in rows if x["fetch"] == "client")} built client-side')


if __name__ == '__main__':
    sys.exit(main())
