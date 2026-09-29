#!/usr/bin/env python3
"""#65 results.json from bms_batch runs (raw runs/ are gitignored; excerpts go to evidence/).

  summarize.py <controls-run-id> <apps-run-id>
"""
import hashlib, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERIAL = '5cd1e3dd00000000000000000923012c'
EVID = HERE / 'evidence'
MARKERS = {  # INVENTORY item -> positive log marker
    '1': r'\[B8-PM\] projected getProviderInfo',
    '2': r'\[B8-PM\] projected resolveContentProvider',
    '3': r'\[B8-PROV\] bind providers=\d+ metaData filled=[1-9]',
    '4': r'\[B7\] nativeLibraryDir .* does not exist; using',
    '6': r'\[B8-SVC\] appops answered in process',
    '7': r'\[B8-SVC\] (uimode|locale|account|alarm) answered in process',
    '15': r'\[B8-COMPAT\] targetSdk=\d+ disabledCompatChanges=[1-9]',
}
ORIGINAL = {  # the error each item removes
    '1': r'NameNotFoundException: ComponentInfo\{[^}]*/androidx\.startup\.InitializationProvider\}',
    '2': r"Couldn't find meta-data for provider with authority",
    '3': r"Couldn't find meta-data for provider with authority",
    '4': r'Unable to create namespace for the classloader',
    '6': r'No service published for: appops',
    '7': r'No service published for: (uimode|locale|account|alarm)',
    '15': r'NEVER_MATCHES_B8_COMPAT',
}
WHITE = ['fd-etar', 'burgerking', 'ooniprobe', 'fd-fluffychat', 'fd-immich', 'fd-kitchenowl', 'fd-minetest']
B7 = ['opencamera', 'fd-android', 'fd-k9', 'fd-libre', 'fd-saber', 'fd-catima', 'fd-fennec_fdroid']


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def child_lines(hilog, package):
    lines = hilog.read_text(errors='replace').splitlines()
    pids = set()
    for l in lines:
        m = re.search(r'APPSPAWN: \[appspawn_service\.c:\d+\]' + re.escape(package) + r' with pid (\d+)', l)
        if m: pids.add(m.group(1))
        m = re.search(r'^\S+ \S+\s+(\d+)\s+\d+ . C00f00/AppSpawnXJava: \[stderr\] \[B43-BIND\] ensureBindApplication start bundle='
                      + re.escape(package) + r'$', l)
        if m: pids.add(m.group(1))
    return [(n, l) for n, l in enumerate(lines, 1)
            if len(l.split()) > 3 and (l.split()[2] in pids or (package in l and 'APPSPAWN' in l))], pids


def first(rows, pattern, limit=1):
    rx = re.compile(pattern)
    return [{'line': n, 'text': l[:500]} for n, l in rows if rx.search(l)][:limit]


def app_record(run_dir, key):
    d = run_dir / key
    rec = json.loads((d / 'record.json').read_text())
    hilog = d / 'hilog.txt'
    out = {'status': rec.get('status'), 'observed_pids': rec.get('observed_pids'),
           'install': rec.get('install'), 'record': str(d / 'record.json'),
           'screens': [s.get('path') for s in rec.get('screenshots', []) if s.get('path')],
           'visual_verdict': 'pending_review'}
    if not hilog.exists():
        out['error'] = 'no hilog'; return out
    rows, pids = child_lines(hilog, rec['package'])
    out['hilog'] = {'file': str(hilog), 'sha256': sha(hilog), 'child_pids': sorted(pids)}
    out['markers'] = {item: first(rows, pat) for item, pat in MARKERS.items()}
    out['original_error_counts'] = {item: sum(1 for _, l in rows if re.search(pat, l)) for item, pat in ORIGINAL.items()}
    out['schedule_launch_ability'] = first(rows, r'\[BRIDGED\] ScheduleLaunchAbility|\[B47-SLA\] ENTRY')
    out['first_frame'] = first(rows, r'OH_SwapHijack|nativeQueueBuffer|QueueBuffer OK|first frame|reportFullyDrawn')
    out['next_wall'] = first(rows, r'J_invokeStaticMain_main_threw|Caused by: |exit with (code|signal)', limit=3)
    return out


def main():
    ctl, apps = HERE / 'runs' / sys.argv[1] / SERIAL, HERE / 'runs' / sys.argv[2] / SERIAL
    build = json.loads((HERE.parent / '2026-09-29-bms-link-entry-walls/build-result-r7b.json').read_text())
    res = {'serial': SERIAL, 'generation': '6cb40cd610ec29a69e320b8cc7d766ccffc675cbd7e94b709cc5d2462b9cddb0',
           'overlay': {'sha256': build['output_sha256'], 'baseline_sha256': build['baseline_sha256']},
           'runs': {'controls': str(ctl), 'apps': str(apps)}, 'apps': {}}
    for key in WHITE + B7:
        if (apps / key / 'record.json').exists():
            res['apps'][key] = app_record(apps, key)
    res['no_regression'] = {k: app_record(ctl, k) for k in ('helloworld', 'zigzag') if (ctl / k / 'record.json').exists()}
    res['effective'] = {}
    for item in MARKERS:
        hits = [(k, v['markers'][item][0]) for k, v in list(res['apps'].items()) + list(res['no_regression'].items())
                if v.get('markers', {}).get(item)]
        orig = sum(v.get('original_error_counts', {}).get(item, 0) for v in res['apps'].values())
        res['effective'][item] = {'apps_with_marker': [k for k, _ in hits],
                                  'marker_lines': [dict(app=k, **line) for k, line in hits[:3]],
                                  'original_error_count': orig}
    res['white_window'] = {k: {'schedule_launch_ability': bool(res['apps'][k]['schedule_launch_ability']),
                               'first_frame': bool(res['apps'][k]['first_frame']),
                               'evidence': (res['apps'][k]['schedule_launch_ability'] + res['apps'][k]['first_frame'])[:2]}
                           for k in WHITE if k in res['apps'] and 'markers' in res['apps'][k]}
    res['lit_count'] = None
    res['outer_signed_lit_count'] = None
    (HERE / 'results.json').write_text(json.dumps(res, indent=1, ensure_ascii=False) + '\n')
    EVID.mkdir(exist_ok=True)
    for key, v in list(res['apps'].items()) + list(res['no_regression'].items()):
        if 'markers' not in v: continue
        lines = [f'# {key} {v["hilog"]["file"]} sha256={v["hilog"]["sha256"]}']
        for item, hits in v['markers'].items():
            lines += [f'[item {item}] {h["line"]}: {h["text"]}' for h in hits]
        lines += [f'[next] {h["line"]}: {h["text"]}' for h in v['next_wall']]
        (EVID / (key + '.txt')).write_text('\n'.join(lines) + '\n')
    for item, e in res['effective'].items():
        print(item, len(e['apps_with_marker']), 'apps, original', e['original_error_count'])


if __name__ == '__main__':
    main()
