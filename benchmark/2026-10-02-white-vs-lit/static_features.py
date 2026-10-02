#!/usr/bin/env python3
"""Existing static/structural features joined onto the same WHITE/LIT groups (population.groups()).

    static_features.py

  trampoline     benchmark/2026-10-01-trampoline-scan/results.json (66 original keys only): launcher onCreate starts
                 another Activity (possible-lifecycle-trampoline) / none found / unknown / not scanned
  b10_*          benchmark/2026-10-01-b10-theme-graphics/PREDICTIONS.csv (166 keys): startup / later ActionBar-theme
                 candidates, unanchored setSupportActionBar, graphics-constructor families referenced
  apk_*          class_defs / type refs of every classes*.dex in the frozen APK (B10 collect.inputs locates the 166
                 APKs; java_classes.dex_types reads the dex): compose (defines AndroidComposeView), appcompat (defines
                 AppCompatActivity), webview_ref (references android.webkit.WebView), capacitor / cordova (defines
                 com.getcapacitor.Bridge / org.apache.cordova.CordovaWebView), gdx (com.badlogic.gdx), glsurface_ref
                 (references android.opengl.GLSurfaceView), flutter (io.flutter.embedding), react (com.facebook.react)
                 -- the U10.1T8 runtime logs no class_linker lines, so Compose/AppCompat use is read from the APK
  webview_full / surface_full / content_leaves=0   vrt.py on the run (content of the final view tree)
  two_sessions   the run created >= 2 app window sessions (features-per-key.csv sessions_created)
Writes static-features.csv (per key) and prints WHITE vs LIT rates with one-sided Fisher p.
"""
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
import population  # noqa: E402
import templates  # noqa: E402
import vrt  # noqa: E402
sys.path.insert(0, str(REPO / 'benchmark/2026-10-01-b10-theme-graphics'))
sys.path.insert(0, str(REPO / 'benchmark/2026-10-02-toutiao-oldroute-diff'))
sys.path.insert(0, str(REPO / 'scripts/lab'))
import collect as b10_collect  # noqa: E402
import java_classes  # noqa: E402
import lab_paths  # noqa: E402
import zipfile  # noqa: E402

APK_DEFINES = {'apk_compose': 'Landroidx/compose/ui/platform/AndroidComposeView;',
               'apk_appcompat': 'Landroidx/appcompat/app/AppCompatActivity;',
               'apk_capacitor': 'Lcom/getcapacitor/Bridge;', 'apk_cordova': 'Lorg/apache/cordova/CordovaWebView;',
               'apk_flutter': 'Lio/flutter/embedding/android/FlutterActivity;',
               'apk_react': 'Lcom/facebook/react/ReactActivity;'}
APK_DEFINES_PREFIX = {'apk_gdx': 'Lcom/badlogic/gdx/'}
APK_REFS = {'apk_webview_ref': 'Landroid/webkit/WebView;', 'apk_glsurface_ref': 'Landroid/opengl/GLSurfaceView;'}


def apk_features():
    out = {}
    for row in b10_collect.inputs(lab_paths.workspaces()):
        defined, refs = set(), set()
        with zipfile.ZipFile(row['path']) as z:
            for n in z.namelist():
                if n.startswith('classes') and n.endswith('.dex'):
                    d, r = java_classes.dex_types(z.read(n))
                    defined |= d
                    refs |= r
        f = {k: v in defined for k, v in APK_DEFINES.items()}
        f.update({k: any(x.startswith(v) for x in defined) for k, v in APK_DEFINES_PREFIX.items()})
        f.update({k: v in refs for k, v in APK_REFS.items()})
        out[row['key']] = f
    return out

TRAMP = REPO / 'benchmark/2026-10-01-trampoline-scan/results.json'
B10 = REPO / 'benchmark/2026-10-01-b10-theme-graphics/PREDICTIONS.csv'


def main():
    tr = json.loads(TRAMP.read_text())
    tramp = {}
    for k in tr['candidate_keys']:
        tramp[k] = 'trampoline'
    for k in tr.get('additional_java_negative', []) or []:
        tramp.setdefault(k if isinstance(k, str) else k.get('key'), 'none-found')
    b10 = {r['key']: r for r in csv.DictReader(open(B10))}
    sess = {r['key']: int(r['sessions_created']) for r in csv.DictReader(open(HERE / 'features-per-key.csv'))}
    apk = apk_features()
    rows = []
    for key, g, v, run in population.groups():
        t = templates.extract(run)
        f = vrt.features(run)
        b = b10.get(key, {})
        rows.append({
            'key': key, 'group': g, 'verdict': v,
            'trampoline': tramp.get(key, 'not-scanned' if key not in json.dumps(tr) else 'none-found'),
            'b10_startup_actionbar_theme': int(b.get('startup_actionbar_theme') or 0) > 0,
            'b10_later_actionbar_theme': int(b.get('later_actionbar_theme') or 0) > 0,
            'b10_unanchored_actionbar': int(b.get('unanchored_actionbar') or 0) > 0,
            'b10_graphics_families': len([x for x in (b.get('graphics_constructor_ids') or '').split(';') if x]),
            **apk.get(key, {}),
            'webview_full': f['webview_full'] > 0, 'surface_full': f['surface_full'] > 0,
            'no_content_leaves': f['content_leaves'] == 0, 'two_sessions': sess.get(key, 0) >= 2,
        })
    with open(HERE / 'static-features.csv', 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    nW = sum(r['group'] == 'WHITE' for r in rows)
    nL = sum(r['group'] == 'LIT' for r in rows)
    print(f'WHITE {nW}, LIT {nL}')
    tests = [(n, (lambda r, n=n: r[n] is True)) for n in ('b10_startup_actionbar_theme', 'b10_later_actionbar_theme',
                                                         'b10_unanchored_actionbar', *APK_DEFINES, *APK_DEFINES_PREFIX, *APK_REFS, 'webview_full',
                                                         'surface_full', 'no_content_leaves', 'two_sessions')]
    tests.append(('trampoline (scanned keys only)', lambda r: r['trampoline'] == 'trampoline'))
    tests.append(('b10_graphics_families>=10', lambda r: r['b10_graphics_families'] >= 10))
    for name, pred in tests:
        pool = [r for r in rows if not name.startswith('trampoline') or r['trampoline'] != 'not-scanned']
        w = sum(1 for r in pool if r['group'] == 'WHITE' and pred(r))
        l = sum(1 for r in pool if r['group'] == 'LIT' and pred(r))
        pw = sum(r['group'] == 'WHITE' for r in pool)
        pl = sum(r['group'] == 'LIT' for r in pool)
        print(f'  {name:32} white {w:2}/{pw:<3} lit {l:3}/{pl:<3} p(white high)={population.fisher_one_sided(w, pw - w, l, pl - l):.2g}'
              f'  p(lit high)={population.fisher_one_sided(pw - w, w, pl - l, l):.2g}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
