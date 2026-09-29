#!/usr/bin/env python3
"""INVENTORY.md table -> inventory.json, plus the port record of each item ported in #65.

Every row keeps the survey's own columns verbatim; `port` is added for the items this lane
carried into the route-A runtime JAR overlay, `not_ported_reason` for the rest.
"""
import json, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
COLS = ['id', 'fix', 'symptom', 'westlake', 'route_a', 'status', 'port_approach']
OVERLAY = 'benchmark/2026-09-29-bms-link-entry-walls/build-result-r7b.json'
SRC = 'bms/src/adapter/framework/activity/java/'
PORTED = {
    1: {'files': [SRC + 'ManifestComponentProjection.java', SRC + 'SelfComponentFallback.java'],
        'source': '00.Workspace cd5b32935 src/adapter/framework/activity/java/ManifestComponentProjection.java '
                  '(verbatim) + the component parse loop of InstalledApkApplicationProjection',
        'hook': 'PackageManagerProjectionProxy.invoke: SelfComponentFallback.apply after the delegate call '
                '(null self-package answers only)', 'evidence_marker': '[B8-PM] projected getProviderInfo'},
    2: {'files': [SRC + 'SelfComponentFallback.java'], 'source': 'same as item 1 (resolveProvider)',
        'hook': 'same as item 1', 'evidence_marker': '[B8-PM] projected resolveContentProvider'},
    3: {'files': [SRC + 'B8BindExtras.java'], 'source': 'new: manifest metaData + real appInfo into AppBindData.providers',
        'hook': 'after setField(data, "providers", ...) in ensureBindApplication', 'evidence_marker': '[B8-PROV]'},
    4: {'files': [SRC + 'B7BindFixes.java'], 'source': 'B7 #54 (nativeLibraryDir -> package code dir)',
        'hook': 'ensureBindApplication after "resolved ApplicationInfo"', 'evidence_marker': '[B7] nativeLibraryDir'},
    6: {'files': [SRC + 'LocalServiceBinders.java', SRC + 'B8BindExtras.java'],
        'source': 'Westlake e5666e4 framework/core/java/LocalServiceBinders.java (package adapter.activity, '
                  'thermalservice case dropped, six hidden-API uses via reflection)',
        'hook': 'B7BindFixes.apply -> B8BindExtras.installServiceStubs (sCache only when getService is null)',
        'evidence_marker': '[B8-SVC] appops'},
    7: {'files': [SRC + 'LocalServiceBinders.java', SRC + 'B8BindExtras.java'], 'source': 'same as item 6',
        'hook': 'same as item 6 (uimode, locale, account, alarm)', 'evidence_marker': '[B8-SVC]'},
    15: {'files': [SRC + 'CompatChangeTable.java', SRC + 'B8BindExtras.java'],
         'source': 'Westlake e5666e4 framework/activity/java/CompatChangeTable.java (verbatim)',
         'hook': 'after setField(data, "disabledCompatChanges", new long[0])', 'evidence_marker': '[B8-COMPAT]'},
}
NOT_PORTED = {
    5: 'handled by generation, not by the runtime JAR: bridge 84695d62 pairs with its provider '
       '(single-library swap measured: admission failed, exit 123; #54); all boards move to 6cb40cd6 (#66)',
    8: 'later batch (X/Twitter only)', 9: 'later batch, low priority', 10: 'already present in route-A',
    11: 'needs OH network native side; later batch', 12: 'after first frame', 13: 'later batch',
    14: 'later batch (settings provider)', 16: 'later batch', 17: 'present with a different mechanism; equivalence unchecked',
    18: 'different mechanism, left as is', 19: 'later batch; the Impeller=false injection had no effect on Westlake',
    20: 'BCP change (WindowSessionAdapter) needs a boot image rebuild; after first frame',
    21: 'B6 scope (signal chain)', 22: 'direct-launch only, not applicable to route-A',
    23: 'native / Toutiao-only, out of B8 scope',
}


def main():
    rows = []
    for line in (HERE / 'INVENTORY.md').read_text().splitlines():
        if not line.startswith('| ') or line.startswith('| #') or set(line) <= set('|- '):
            continue
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells) != len(COLS):
            continue
        row = dict(zip(COLS, cells))
        num = int(re.match(r'\d+', row['id']).group())
        row['num'] = num
        if num in PORTED:
            build = json.loads((HERE.parents[1] / OVERLAY).read_text())
            row['port'] = dict(PORTED[num], overlay=OVERLAY, overlay_sha256=build['output_sha256'],
                               overlay_baseline_sha256=build['baseline_sha256'], board_evidence='pending (#66 generation)')
        else:
            row['not_ported_reason'] = NOT_PORTED[num]
        rows.append(row)
    assert [r['num'] for r in rows] == list(range(1, 24)), [r['num'] for r in rows]
    (HERE / 'inventory.json').write_text(json.dumps({'source': 'INVENTORY.md', 'items': rows}, indent=1, ensure_ascii=False) + '\n')
    print(len(rows), 'items;', sum('port' in r for r in rows), 'ported')


if __name__ == '__main__':
    main()
