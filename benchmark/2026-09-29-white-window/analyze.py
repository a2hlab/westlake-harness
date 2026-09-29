#!/usr/bin/env python3
"""Offline evidence index; absence of a marker is never a stall verdict."""
import argparse
import hashlib
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASELINE = REPO / 'benchmark/2026-09-28-bms-route-deploy/spawn-ab/evidence/helloworld/hilog.txt'
HEADER = re.compile(r'^(\d\d-\d\d [\d:.]+)\s+(\d+)\s+(\d+)\s+([DIWEF])\s+([^:]+):\s*(.*)$')
# An observation inventory, NOT a total execution order: bind and ability delivery overlap.
STAGES = {
    'init': r'initChild: proc=',
    'attach': r'attachApplication ENTRY',
    'launch_application': r'\[BRIDGED\] ScheduleLaunchApplication ->',
    'bind_main': r'main-looper iter: ensureBindApplication run',
    'bind_ok': r'\[B43-BIND\] handleBindApplication returned OK',
    'bind_failed': r'\[B43-BIND\] ensureBindApplication FAILED:',
    'ability_stage': r'\[BRIDGED\] ScheduleAbilityStage\(',
    'launch_ability': r'\[BRIDGED\] ScheduleLaunchAbility\(',
    'launch_transaction': r'LaunchActivity transaction scheduled:',
    'main_sentinel': r'MAIN_LOOPER_SENTINEL_RAN',
    'resume_listener': r'activityResumed: OnDrawListener attached',
    'vsync_init': r'OH_DER_VSync: nativeInit ENTRY',
    'vsync_request': r'OH_DER_VSync: scheduleVsync calling RequestFrame',
    'vsync_callback': r'OH_DER_VSync: onOhVsync ENTRY',
    'window_session': r'ENTER WMClient.createSession',
    'content_surface': r'created self-drawing content child=',
    'surface_control': r'relayout: created persistent SurfaceControl',
    'set_surface_node': r'SetSurfaceNode',
    'egl_surface': r'eglCreateWindowSurface:.* -> EGLSurface=',
    'first_frame_notification': r'activityResumed \(first-frame\): OH AbilityTransitionDone',
}
CATEGORIES = {
    'lifecycle': r'ScheduleLaunch|B43-|B47-|onCreate|onResume|activityResumed|activityPaused|activityStopped',
    'vsync_choreographer': r'Choreographer|VSync|Vsync|RequestNextVSync|RequestFrame',
    'skipped_frames': r'Skipped \d+ frames|Skipped frames',
    'anr': r'\bANR\b|Application Not Responding',
    'binder_timeout': r'(?i)binder.*time.?out|time.?out.*binder',
    'window_surface': r'WindowManager|WindowMgr|WMClient|SceneSession|SetSurfaceNode|SurfaceBridge',
    'render_service_errors': r'RSNode|RenderService|Rosen|RSRender|EglHijack',
}

def digest(path):
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}

def parse(path):
    lines = path.read_text(errors='replace').splitlines()
    rows = []
    for i, line in enumerate(lines, 1):
        m = HEADER.match(line)
        if m:
            stamp, pid, tid, level, tag, message = m.groups()
            rows.append(dict(line=i, time=stamp, pid=int(pid), tid=int(tid), level=level,
                             tag=tag, message=message, text=line))
    return lines, rows

def execution(row):
    return 'OH_RegHook' not in row['tag'] and not re.match(r'(?:\[stderr\]\s*)?at\s', row['message'])

def summarize(rows):
    return {'count': len(rows), 'first': rows[0] if rows else None, 'last': rows[-1] if rows else None}

def inspect(path, pid, package):
    if not path.is_file():
        return {'status': 'input_unavailable', 'source': str(path), 'first_unobserved_launch_marker': None}
    lines, all_rows = parse(path)
    rows = [r for r in all_rows if r['pid'] == pid]
    identity = [r for r in rows if f'initChild: proc={package} ' in r['message']]
    if len(identity) != 1:
        return {'status': 'identity_rejected', 'source': digest(path), 'identity_matches': len(identity),
                'first_unobserved_launch_marker': None}
    live = [r for r in rows if execution(r)]
    stages = {name: summarize([r for r in live if re.search(pattern, r['text'])])
              for name, pattern in STAGES.items()}
    categories = {}
    for name, pattern in CATEGORIES.items():
        hits = [r for r in live if re.search(pattern, r['text'])]
        if name == 'render_service_errors':
            hits = [r for r in hits if r['level'] in 'WEF' or re.search(r'(?i)error|fail', r['message'])]
        categories[name] = summarize(hits)
    chain = ['launch_ability', 'launch_transaction', 'resume_listener', 'vsync_init',
             'vsync_request', 'vsync_callback', 'window_session', 'content_surface',
             'surface_control', 'egl_surface', 'first_frame_notification']
    return {'status': 'observed', 'source': digest(path), 'total_lines': len(lines),
            'pid': pid, 'package': package, 'identity': identity[0],
            'file_first': all_rows[0]['time'], 'file_last': all_rows[-1]['time'],
            'target': summarize(rows), 'main': summarize([r for r in rows if r['tid'] == pid]),
            'stages': stages, 'categories': categories,
            'first_unobserved_launch_marker': next((s for s in chain if not stages[s]['count']), None),
            'causes': [r for r in live if 'Caused by:' in r['message']],
            'tail': rows[-50:],
            'package_system_window': summarize([r for r in all_rows if r['pid'] != pid
                and package in r['message'] and re.search(r'(?i)SceneSession|starting.?window|SetSurfaceNode', r['text'])]),
            'scope': 'Exact PID in the assigned capture; stack frames and registration excluded from stage counts. Marker absence is not execution impossibility.'}

def build(root):
    manifest = json.loads((HERE / 'evidence/probe48-targets.json').read_text())
    apps = []
    for row in manifest['apps']:
        p = root / row['key'] / 'hilog.txt'
        result = inspect(p, row['pids_at_15s'][0], row['package'])
        result['key'] = row['key']
        if result['status'] == 'observed':
            causes = '\n'.join(r['message'] for r in result['causes'])
            if not result['stages']['bind_failed']['count']:
                result['observed_bind_error_family'] = None
            elif 'app_search_paths path is not an existing directory' in causes:
                result['observed_bind_error_family'] = 'classloader_namespace_nonexistent_directory'
            elif 'NameNotFoundException' in causes and 'androidx.startup.InitializationProvider' in causes:
                result['observed_bind_error_family'] = 'startup_provider_component_lookup'
            elif "Couldn\u0027t find meta-data for provider" in causes:
                result['observed_bind_error_family'] = 'fileprovider_metadata_lookup'
            else:
                result['observed_bind_error_family'] = 'other_bind_exception'
        record = root / row['key'] / 'record.json'
        if record.exists():
            actual = json.loads(record.read_text())
            assert all(actual[k] == row[k] for k in row), (row['key'], 'record mismatch')
            result['record'] = digest(record)
        apps.append(result)
    timeouts, scanned = [], []
    seen = set()
    # Delayed AMS failures occur in the NEXT app's whole-board capture.
    for path in sorted(root.glob('*/hilog.txt')):
        scanned.append(digest(path))
        for i, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
            if 'lifecycle_timeout,' not in line or line in seen:
                continue
            for row in manifest['apps']:
                pid = row['pids_at_15s'][0]
                if (f'pid: {pid},' in line and f'uid: {row["uid"]},' in line
                        and f'packageName: {row["package"]},' in line):
                    timeouts.append({'key': row['key'], 'source': str(path), 'line': i, 'text': line})
                    seen.add(line)
    return {'task': 61, 'device_access': False, 'visual_verdict': 'not_performed',
            'r2': {'log_observations': 'verified_against_read_only_sources',
                   'exact_handshake_defect': 'unverified_requires_item60',
                   'repair_effect': 'not_tested', 'remaining_four_apps': 'input_not_available'},
            'baseline': inspect(BASELINE, 25183, 'com.example.helloworld'), 'apps': apps,
            'delayed_ams_timeouts': timeouts, 'cross_capture_inputs': scanned,
            'uncovered_white_window_keys': ['fd-binaryeye', 'fd-mobile', 'localsend', 'noice']}

def save(result, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / 'results.json').write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    evidence = out / 'evidence'
    evidence.mkdir(exist_ok=True)
    for app in [result['baseline'], *result['apps']]:
        if app['status'] != 'observed':
            continue
        selected = {r['line']: r for r in app['tail'] + app['causes'] + [app['identity']]}
        for bucket in [*app['stages'].values(), *app['categories'].values(), app['package_system_window']]:
            for r in [bucket['first'], bucket['last']]:
                if r:
                    selected[r['line']] = r
        key = app.get('key', 'helloworld')
        (evidence / f'{key}.txt').write_text('SOURCE ' + app['source']['path'] + '\nSHA256 '
            + app['source']['sha256'] + '\nOriginal source line numbers follow.\n'
            + '\n'.join(f'{i}: {r["text"]}' for i, r in sorted(selected.items())) + '\n')
    (evidence / 'delayed-ams-timeouts.txt').write_text('\n'.join(
        f'{r["key"]} {r["source"]}:{r["line"]}\n{r["text"]}' for r in result['delayed_ams_timeouts']) + '\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.input_root.resolve()):
        parser.error('Output must be outside the read-only input root')
    save(build(args.input_root), args.output)
