#!/usr/bin/env python3
"""Validate on the whole U10.1T8 stage-A surface: which features separate the white keys from the lit keys?

    population.py [--out-dir .]

Keys: benchmark/2026-10-02-double-copy-universality/per-key.csv (group = cluster 0 or not); run per key =
benchmark/2026-10-02-u10-1-t8-sweep/u10-1-t8-reference/sources.json (the run that carried the signed verdict -- per-key's
run_dir is the FIRST signing window's run, e.g. wikipedia window 1 = white while the verdict is lit from w5 r1). Groups (run-level verdict, not the cluster label):
  WHITE  cluster 0 (candidate-first-fatal-clusters) AND signed alive-white-window / white / alive-black-window /
         alive-black-content in that run: 16 keys (frequent-habits app_failed and tutanota dead are not windows;
         yahtzeedicer and fd-noice are cluster 0 but signed lit/lottery-lit on this very run -> LIT0)
  LIT    signed lit (116 incl. those two) ; the two smoke keys (unsigned) are left out.
Per key, from templates.py (window launch-3 s .. min(t20, hilog end)):
  * engineered window/render features (FEATURES): counted from the app-scope templates' line counts;
  * every template's presence -> rates in WHITE vs LIT, one-sided Fisher p, kept if present in >= 3 keys.
Writes features-per-key.csv, features.csv (engineered rates) and templates-rate.csv (template scan, top rows).
"""
import argparse
import csv
import math
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths  # noqa: E402
import templates  # noqa: E402

WS = str(lab_paths.workspaces())
PER_KEY = REPO / 'benchmark/2026-10-02-double-copy-universality/per-key.csv'
SOURCES = REPO / 'benchmark/2026-10-02-u10-1-t8-sweep/u10-1-t8-reference/sources.json'
WHITE_VERDICTS = {'alive-white-window', 'white', 'alive-black-window', 'alive-black-content'}

# name -> (scope, regex over the normalised template); value = summed line count of matching templates
FEATURES = {
    'sessions_created': ('app', r'OH_WindowMgrClient: createSession: success, sessionId='),
    'empty_surface': ('app', r'BBQ\.getSurface: ohNativeWindow null'),
    'surface_rescued': ('app', r'BBQ\.update: sessionId=<N> → OHNativeWindow='),
    'egl_window_surface': ('app', r'OH_EglHijack: eglCreateWindowSurface: dpy='),
    'first_frame': ('app', r'activityResumed \(first-frame\)'),
    'resumed_callbacks': ('app', r'OH callback \(direct token\): state=INITIAL->FOREGROUND -> RESUMED'),
    'wsa_relayout': ('app', r'^I C00f00/OH_LifecycleAdapter|AppSpawnXJava: \[stderr\] \[OH_WSA-relayout\]'),
    'rs_composed_app_buffer': ('sys', r'RSBaseRenderUtil::DealWithSurfaceRotationAndGravity'),
    'wms_foreground_invalid': ('sys', r'WMSLife: session\.cpp Foreground: Foreground state invalid'),
    'window_state_error': ('sys', r'process event \[WINDOWMANAGER, WINDOW_STATE_ERROR'),
    'surfaceview_class': ('app', r'^CLS android\.view\.SurfaceView(\$|$)'),
    'glsurfaceview_class': ('app', r'^CLS android\.opengl\.GLSurfaceView(\$|$)'),
    'textureview_class': ('app', r'^CLS android\.view\.TextureView(\$|$)'),
    'compose_view_class': ('app', r'^CLS androidx\.compose\.ui\.platform\.AndroidComposeView(\$|$)'),
    'webview_class': ('app', r'^CLS android\.webkit\.WebView(\$|$)'),
    'egl_iae': ('app', r'IllegalArgumentException.*(eglCreateWindowSurface|Make sure the SurfaceView)'),
}
FEATURES['wsa_relayout'] = ('app', r'\[OH_WSA-relayout\]')


def fisher_one_sided(a, b, c, d):
    """P(X >= a) for the 2x2 table [[a, b], [c, d]] (a = WHITE with feature) -- hypergeometric upper tail."""
    n1, n2, k = a + b, c + d, a + c
    total = n1 + n2

    def lc(n, r):
        return math.lgamma(n + 1) - math.lgamma(r + 1) - math.lgamma(n - r + 1)
    denom = lc(total, k)
    return sum(math.exp(lc(n1, x) + lc(n2, k - x) - denom) for x in range(a, min(n1, k) + 1))


def groups():
    import json
    src = json.loads(SOURCES.read_text())['keys']
    out = []
    for r in csv.DictReader(open(PER_KEY)):
        t20 = (src.get(r['key']) or {}).get('t20')
        r['run_dir'] = str(Path(t20).parent) if t20 else r['run_dir']
        v = r['signed_verdict']
        if r['group'] == 'white-cluster' and v in WHITE_VERDICTS:
            g = 'WHITE'
        elif v in ('lit', 'lottery') and r['group'] in ('lit', 'white-cluster'):
            g = 'LIT'
        else:
            continue
        out.append((r['key'], g, v, r['run_dir'].replace('$WORKSPACES', WS)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out-dir', type=Path, default=HERE)
    ap.add_argument('--top', type=int, default=30)
    a = ap.parse_args()
    keys = groups()
    feats, presence = {}, {}
    skipped = []
    for key, g, v, run in keys:
        if not (Path(run) / 'hilog.txt').is_file():
            skipped.append(key)
            continue
        t = templates.extract(run)
        f = {}
        for name, (scope, rx) in FEATURES.items():
            r = re.compile(rx)
            f[name] = sum(n for tpl, n in t[scope].items() if r.search(tpl))
        feats[key] = (g, v, f, t['cut_by'], round((t['cutoff'] or 0) - (t['start'] or 0), 1))
        presence[key] = {('app', k) for k in t['app']} | {('sys', k) for k in t['sys']}
    nW = sum(1 for k in feats.values() if k[0] == 'WHITE')
    nL = sum(1 for k in feats.values() if k[0] == 'LIT')
    with open(a.out_dir / 'features-per-key.csv', 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['key', 'group', 'verdict', 'cut_by', 'window_s', *FEATURES])
        for key, (g, v, f, cb, ws) in sorted(feats.items(), key=lambda x: (x[1][0], x[0])):
            w.writerow([key, g, v, cb, ws, *(f[n] for n in FEATURES)])
    rows = []
    for name in FEATURES:
        for thr in (1, 2):
            wy = sum(1 for g, v, f, *_ in feats.values() if g == 'WHITE' and f[name] >= thr)
            ly = sum(1 for g, v, f, *_ in feats.values() if g == 'LIT' and f[name] >= thr)
            rows.append({'feature': f'{name}>={thr}', 'white': f'{wy}/{nW}', 'lit': f'{ly}/{nL}',
                         'white_rate': round(wy / nW, 2), 'lit_rate': round(ly / nL, 2),
                         'p_white_high': f'{fisher_one_sided(wy, nW - wy, ly, nL - ly):.2g}',
                         'p_lit_high': f'{fisher_one_sided(nW - wy, wy, nL - ly, ly):.2g}'})
    with open(a.out_dir / 'features.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    # template scan
    allt = {}
    for key, (g, *_rest) in feats.items():
        for t in presence[key]:
            allt.setdefault(t, [0, 0])[0 if g == 'WHITE' else 1] += 1
    scan = []
    for t, (wy, ly) in allt.items():
        if wy + ly < 3:
            continue
        scan.append({'scope': t[0], 'template': t[1][:220], 'white': f'{wy}/{nW}', 'lit': f'{ly}/{nL}',
                     'white_rate': round(wy / nW, 2), 'lit_rate': round(ly / nL, 2),
                     'p_white_high': fisher_one_sided(wy, nW - wy, ly, nL - ly),
                     'p_lit_high': fisher_one_sided(nW - wy, wy, nL - ly, ly)})
    m = len(scan)
    for side in ('p_white_high', 'p_lit_high'):
        scan.sort(key=lambda r: r[side])
        print(f'== template scan, {side} (of {m} templates in >= 3 keys; Bonferroni 0.05 -> p < {0.05 / m:.1e})')
        for r in scan[:a.top]:
            print(f"  p={r[side]:.1e} white {r['white']:6} lit {r['lit']:7} {r['scope']} {r['template'][:140]}")
    scan.sort(key=lambda r: min(r['p_white_high'], r['p_lit_high']))
    with open(a.out_dir / 'templates-rate.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(scan[0]))
        w.writeheader()
        for r in scan[:400]:
            w.writerow({**r, 'p_white_high': f"{r['p_white_high']:.2g}", 'p_lit_high': f"{r['p_lit_high']:.2g}"})
    print(f'groups: WHITE {nW}, LIT {nL}; no hilog (left out): {skipped}')
    for r in rows:
        if r['feature'].endswith('>=1'):
            print(f"  {r['feature']:28} white {r['white']:6} lit {r['lit']:8} p(white high)={r['p_white_high']:7} p(lit high)={r['p_lit_high']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
