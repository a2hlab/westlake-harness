#!/usr/bin/env python3
"""White/black residual (cluster C15 of 2026-10-03-u13-first-fatal-clusters) vs the latest lit runs: one row per run,
the window/content features of every white mechanism found so far, extracted by the tools that found them (imported,
not copied):
  M1  multi-window misroute       white-vs-lit/multiwin.py analyse()      top Activity's VRI gets the empty Surface
  M2  full-screen WebView         white-vs-lit/vrt.py features()          webview_full (+ the provider proxy marker)
  M3  GLSurfaceView EGL IAE       white-m3-glsurfaceview (marker)         'GLSurfaceView: ...IllegalArgumentException: Make sure'
  M4  no window session           white-unexplained-4/evidence.py scan()  0 createSession successes for the app pids
  M5  dialog before main window   white-unexplained-4/evidence.py         dialog_before_main (androidType 2 first)
  M6  dropped close of the top    white-m6-finish-return/closes.py scan() class top_dropped
plus surface_full (a SurfaceView/GLSurfaceView covering >= half the screen), content_leaves and text_views.

    features.py [--out-dir .]

Population
  residual  the 9 keys of C15, their latest U12 stage-A run (none of them ran in U13 windows 1-2)
  lit       every U13 window-1/window-2 run (5ea, 5cd, 61b) of a key the outer signed lit in all its runs
"""
import argparse
import glob
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
B = REPO / 'benchmark'
for d in ('2026-10-02-white-vs-lit', '2026-10-02-white-m6-finish-return', '2026-10-02-white-unexplained-4'):
    sys.path.insert(0, str(B / d))
sys.path.insert(0, str(REPO / 'scripts/lab'))
import closes  # noqa: E402
import evidence  # noqa: E402
import lab_paths  # noqa: E402
import multiwin  # noqa: E402
import templates  # noqa: E402
import vrt  # noqa: E402

WS = lab_paths.workspaces()
EXE = WS / 'westlake-harness-u7-executor/benchmark/2026-10-03-u13-stage-a-plan'
SIGN = B / '2026-10-03-u13-stage-a-plan'
RESIDUAL = ['cv2-ca-vaults-randomlydie', 'cv2-com-bytehamster-flowitgame', 'cv2-com-degeder-yam',
            'cv2-com-paultirk-yatoo', 'cv2-dev-obfusk-jiten-webview', 'cv2-timur-webrtc-check', 'fd-app',
            'fd-shatteredpixeldungeon', 'fd-tutanota']
IAE = 'GLSurfaceView: java.lang.IllegalArgumentException: Make sure'
PROXY = re.compile(r'J8-WEBVIEW|J10[e-g]-WEB|B8-WEBVIEW\] WebViewFactory.sProviderInstance seeded')


def row(run, key, population, generation):
    r = {'key': key, 'population': population, 'generation': generation,
         'run': str(run).replace(str(WS), '$WORKSPACES')}
    try:
        t, out = evidence.scan(run)
    except Exception as e:  # noqa: BLE001
        r['error'] = f'{type(e).__name__}: {e}'
        return r
    pids = set(t['app_pids'])
    iae = proxy = 0
    for line in open(Path(run) / 'hilog.txt', errors='replace'):
        m = templates.LINE.match(line)
        if not m or int(m.group(7)) not in pids:
            continue
        iae += IAE in line
        proxy += bool(PROXY.search(line))
    v, mw, cl, ev = vrt.features(run), multiwin.analyse(run), closes.scan(run), evidence.features(out)
    r.update({'sessions': len(out['windows']), 'android_types': [w['androidType'] for w in out['windows']],
              'M1_misroute': bool(mw.get('misroute')), 'top_outcome': mw.get('top_outcome'),
              'M2_webview_full': bool(v.get('webview_full')), 'webview_proxy_marker': proxy > 0,
              'M3_gl_iae': iae > 0, 'M4_no_session': len(out['windows']) == 0,
              'M5_dialog_before_main': bool(ev['dialog_before_main']), 'M6_top_dropped': cl.get('class') == 'top_dropped',
              'surface_full': bool(v.get('surface_full')), 'content_leaves': v.get('content_leaves'),
              'text_views': v.get('text_views'), 'vrt_roots': v.get('roots'), 'vrt_dumps': v.get('vrt_dumps'),
              'top': mw.get('top'), 'close_class': cl.get('class')})
    return r


def lit_runs():
    lit = {}
    for w in ('window1-signoff', 'window2-signoff'):
        for k, v in json.loads((SIGN / w / 'outer-signoff.json').read_text())['keys'].items():
            if v.get('runs') and v.get('lit_runs') == v.get('runs'):
                lit[k] = True
            elif k in lit:
                lit[k] = False
    out = []
    for rec in sorted(glob.glob(str(EXE / 'window[12]*/u13-*/*/runner/*/*/*/*/record.json'))):
        d = Path(rec).parent
        if '/smoke/' in rec or not lit.get(d.name) or not (d / 'hilog.txt').exists():
            continue
        out.append((d, d.name))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out-dir', default=str(HERE))
    od = Path(ap.parse_args().out_dir)
    src = {r['key']: r for r in json.loads((B / '2026-10-03-u13-first-fatal-clusters/per-run.json').read_text())}
    rows = [row(Path(src[k]['run'].replace('$WORKSPACES', str(WS))), k, 'residual', src[k]['generation'])
            for k in RESIDUAL]
    rows += [row(d, k, 'lit', 'u13') for d, k in lit_runs()]
    (od / 'features.json').write_text(json.dumps(rows, indent=1) + '\n')
    for r in rows[:9]:
        print(json.dumps({k: r.get(k) for k in ('key', 'M1_misroute', 'M2_webview_full', 'webview_proxy_marker',
              'M3_gl_iae', 'M4_no_session', 'M5_dialog_before_main', 'M6_top_dropped', 'surface_full', 'android_types',
              'vrt_roots', 'error')}))
    print('lit runs', sum(r['population'] == 'lit' for r in rows), 'keys', len({r['key'] for r in rows if r['population'] == 'lit'}))


if __name__ == '__main__':
    main()
