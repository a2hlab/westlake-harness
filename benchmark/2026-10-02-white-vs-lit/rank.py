#!/usr/bin/env python3
"""Ranked feature table: white rate, lit rate, Fisher p (U10.1T8 surface) and paired-run support (same app, same
state, one lit one white), plus the per-white-key mechanism table.

    rank.py            # writes ranked-features.csv, white-keys.csv, results.json; prints the tables

Each feature is a function of one run (runtime) or of the APK/scan (static: no paired support possible, the two runs
of a pair share the APK). direction `white` = expected present in white runs, `lit` = expected present in lit runs.
Paired support = pairs (pairs.json: 7 pairs / 4 keys / 11 runs) where the white run has it and the lit run does not
(direction white), or the reverse (direction lit).
"""
import csv
import itertools
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import multiwin  # noqa: E402
import pair_diff  # noqa: E402
import population  # noqa: E402
import templates  # noqa: E402
import vrt  # noqa: E402


def has(scope, rx):
    r = re.compile(rx)
    return lambda run: any(r.search(k) for k in templates.extract(run)[scope])


RUNTIME = [
    # name, direction, mechanism, fn
    ('gl_program_linked (Mali glLinkProgram in the app)', 'lit', 'symptom: the app drew more than a clear',
     has('app', r'OHOSDEBUG-SPRD glLinkProgram start')),
    ('rs_composed_app_buffer (RS DealWithSurfaceRotationAndGravity)', 'lit', 'outcome: RS composed a buffer',
     has('sys', r'RSBaseRenderUtil::DealWithSurfaceRotationAndGravity')),
    ('top_activity_empty_surface (multiwin misroute)', 'white', 'M1 multi-window last-session rescue',
     lambda run: multiwin.analyse(run)['misroute']),
    ('webview_fullscreen_content (VRT)', 'white', 'M2 WebView renders nothing',
     lambda run: vrt.features(run)['webview_full'] > 0),
    ('glsurfaceview_egl_iae (GLSurfaceView eglCreateWindowSurface IAE)', 'white', 'M3 SurfaceView child has no native window',
     has('app', r'GLSurfaceView: java\.lang\.IllegalArgumentException: Make sure the SurfaceView')),
    ('surface_fullscreen_content (VRT SurfaceView/GLView)', 'white', 'M3 SurfaceView child has no native window',
     lambda run: vrt.features(run)['surface_full'] > 0),
    ('no_window_session (no createSession success)', 'white', 'M4 no window added',
     lambda run: not has('app', r'createSession: success, sessionId=')(run)),
    ('no_content_leaves (VRT)', 'white', 'content empty (any cause)',
     lambda run: vrt.features(run)['content_leaves'] == 0),
    ('specified_launch (SceneBoard StartAbilityBySpecified)', 'white', 'association (confounded with M2 shells)',
     has('sys', r'StartAbilityBySpecified: bundleName: <PKG>')),
    ('two_sessions (>= 2 createSession)', 'white', 'control: multi-window alone',
     lambda run: sum(n for k, n in templates.extract(run)['app'].items() if 'createSession: success, sessionId=' in k) >= 2),
    ('window_state_error (WINDOWMANAGER WINDOW_STATE_ERROR)', 'white', 'control',
     has('sys', r'process event \[WINDOWMANAGER, WINDOW_STATE_ERROR')),
]
STATIC = [
    ('apk_glsurfaceview_ref', 'white', 'M3 (static)', lambda s: s['apk_glsurface_ref'] == 'True'),
    ('apk_capacitor_or_cordova', 'white', 'M2 (static)', lambda s: 'True' in (s['apk_capacitor'], s['apk_cordova'])),
    ('apk_gdx (libGDX)', 'white', 'M3 (static)', lambda s: s['apk_gdx'] == 'True'),
    ('apk_compose', 'white', 'control (COMPOSE-WALL refuted 2026-10-01)', lambda s: s['apk_compose'] == 'True'),
    ('apk_appcompat', 'white', 'control', lambda s: s['apk_appcompat'] == 'True'),
    ('b10_later_actionbar_theme', 'white', 'control', lambda s: s['b10_later_actionbar_theme'] == 'True'),
    ('b10_startup_actionbar_theme', 'white', 'control', lambda s: s['b10_startup_actionbar_theme'] == 'True'),
    ('trampoline (66 scanned keys)', 'white', 'control', lambda s: s['trampoline'] == 'trampoline'),
]
OUTER_DOUBLE_COPY = ('double_copy (bridge x2 in maps; outer 2026-10-02, double-copy-universality)', 'white',
                     'control: refuted', '17/17 with maps', '115/115 with maps')


def main():
    groups = population.groups()
    static = {r['key']: r for r in csv.DictReader(open(HERE / 'static-features.csv'))}
    pairs = pair_diff.load_pairs()
    nW = sum(g == 'WHITE' for _, g, _, _ in groups)
    nL = sum(g == 'LIT' for _, g, _, _ in groups)
    rows, per_key = [], {k: {'group': g, 'verdict': v} for k, g, v, _ in groups}
    for name, direction, mech, fn in RUNTIME:
        vals = {k: bool(fn(run)) for k, g, v, run in groups}
        w = sum(vals[k] for k, g, *_ in groups if g == 'WHITE')
        l = sum(vals[k] for k, g, *_ in groups if g == 'LIT')
        sup = 0
        for key, state, lit, white in pairs:
            fl, fw = bool(fn(lit)), bool(fn(white))
            sup += (fw and not fl) if direction == 'white' else (fl and not fw)
        p = population.fisher_one_sided(w, nW - w, l, nL - l) if direction == 'white' else \
            population.fisher_one_sided(nW - w, w, nL - l, l)
        rows.append({'feature': name, 'kind': 'runtime', 'direction': direction, 'mechanism': mech,
                     'white': f'{w}/{nW}', 'lit': f'{l}/{nL}', 'fisher_p': f'{p:.2g}', 'paired_support': f'{sup}/{len(pairs)}',
                     'white_keys': ' '.join(k for k, g, *_ in groups if g == 'WHITE' and vals[k] == (direction == 'white')),
                     'lit_keys_hit': ' '.join(k for k, g, *_ in groups if g == 'LIT' and vals[k] == (direction == 'white'))[:300]})
        for k in vals:
            per_key[k][name.split(' ')[0]] = vals[k]
    for name, direction, mech, fn in STATIC:
        pool = [(k, g) for k, g, *_ in groups if not name.startswith('trampoline') or static[k]['trampoline'] != 'not-scanned']
        pw, pl = sum(g == 'WHITE' for _, g in pool), sum(g == 'LIT' for _, g in pool)
        w = sum(fn(static[k]) for k, g in pool if g == 'WHITE')
        l = sum(fn(static[k]) for k, g in pool if g == 'LIT')
        rows.append({'feature': name, 'kind': 'static', 'direction': direction, 'mechanism': mech,
                     'white': f'{w}/{pw}', 'lit': f'{l}/{pl}', 'fisher_p': f'{population.fisher_one_sided(w, pw - w, l, pl - l):.2g}',
                     'paired_support': 'n/a (same APK)',
                     'white_keys': ' '.join(k for k, g in pool if g == 'WHITE' and fn(static[k])),
                     'lit_keys_hit': ' '.join(k for k, g in pool if g == 'LIT' and fn(static[k]))[:300]})
    rows.append({'feature': OUTER_DOUBLE_COPY[0], 'kind': 'runtime (outer table)', 'direction': 'white',
                 'mechanism': OUTER_DOUBLE_COPY[2], 'white': OUTER_DOUBLE_COPY[3], 'lit': OUTER_DOUBLE_COPY[4],
                 'fisher_p': '1', 'paired_support': '-', 'white_keys': '', 'lit_keys_hit': ''})
    rows.sort(key=lambda r: float(r['fisher_p']))
    with open(HERE / 'ranked-features.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f'WHITE {nW} / LIT {nL}; {len(pairs)} pairs')
    for r in rows:
        print(f"  p={r['fisher_p']:8} white {r['white']:>16} lit {r['lit']:>18} pairs {r['paired_support']:>15}  {r['feature']}")
    # per white key: first matching mechanism
    order = [('top_activity_empty_surface', 'M1 multi-window: top Activity got the empty Surface'),
             ('webview_fullscreen_content', 'M2 full-screen WebView, no renderer'),
             ('glsurfaceview_egl_iae', 'M3 GLSurfaceView Surface invalid (EGL IAE)'),
             ('no_window_session', 'M4 no window session')]
    wk = []
    for k, info in sorted(per_key.items()):
        if info['group'] != 'WHITE':
            continue
        mech = next((label for col, label in order if info.get(col)), 'unexplained')
        wk.append({'key': k, 'verdict': info['verdict'], 'mechanism': mech,
                   **{c: info.get(c) for c, _ in order}, 'gl_program_linked': info.get('gl_program_linked'),
                   'no_content_leaves': info.get('no_content_leaves')})
    with open(HERE / 'white-keys.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(wk[0]))
        w.writeheader()
        w.writerows(wk)
    counts = {}
    for r in wk:
        counts[r['mechanism']] = counts.get(r['mechanism'], 0) + 1
    print('white keys by mechanism:', counts)
    (HERE / 'results.json').write_text(json.dumps({
        'groups': {'WHITE': nW, 'LIT': nL}, 'pairs': len(pairs), 'pair_keys': sorted({p[0] for p in pairs}),
        'mechanism_counts': counts, 'white_keys': {r['key']: r['mechanism'] for r in wk},
        'features': rows}, indent=1) + '\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
