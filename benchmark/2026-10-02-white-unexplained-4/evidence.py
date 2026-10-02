#!/usr/bin/env python3
"""Evidence for the 4 white-cluster keys white-vs-lit could not separate, one key at a time, against the 117 lit keys.

    evidence.py [--out evidence.txt]

Runs = the signing runs (white-vs-lit population.groups()). Per key:
  rare templates  its app/sys templates present in <= 3 of the 117 lit runs (templates.py window), count + first lines
  windows         createSession order with androidType (1 = Activity base window, 2 = TYPE_APPLICATION, i.e. a Dialog),
                  the BBQ lookup outcome per session (m1 static_proof replay), SceneBoard sub-window index -> zOrder
  abilities       AMS ForegroundLifecycle / BackgroundLifecycle order, TerminateAbility, the G2.14as-VIS state per token
  view tree       the final G2.14as-VRT tree (vrt.py)
  render          RS composed app buffers (sys template count), first frame present
Population features this round adds (white / lit):
  dialog_before_main   a type-2 window session is created before the Activity's type-1 window
  caller_left_background  >= 2 abilities came to the foreground and every one ends in background (top one terminated)
  ..._stable              the same, and no lifecycle event in the last 5 s before the cutoff
Static checks (APK, aapt2/dexdump): itsdicey DiceView.onDraw background + the hint TextView's layout visibility;
Jellyfin (fd-mobile) WebViewFragment.showOutdatedWebViewDialog.
"""
import argparse
import re
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WVL = REPO / 'benchmark/2026-10-02-white-vs-lit'
sys.path.insert(0, str(WVL))
sys.path.insert(0, str(REPO / 'benchmark/2026-10-02-m1-session-slots'))
sys.path.insert(0, str(REPO / 'benchmark/2026-10-01-b10-theme-graphics'))
sys.path.insert(0, str(REPO / 'scripts/lab'))
import collect as b10  # noqa: E402
import lab_paths  # noqa: E402
import population  # noqa: E402
import static_proof  # noqa: E402
import templates  # noqa: E402
import vrt  # noqa: E402

KEYS = ['cv2-org-andresoviedo-dddmodel2', 'fd-AppManager', 'fd-mobile', 'cv2-com-emmanuelmess-itsdicey']
CS = re.compile(r'createSession: bundle=\S+ ability=(\S+) name=\S+, androidType=(\d+) -> ohType=(\d+)')
OK = re.compile(r'createSession: success, sessionId=(\d+)')
ZL = re.compile(r'onSubSessionZLevelChange, index: (\d+), Id: (\d+)')
ZO = re.compile(r'UpdateZOrderInner: id: (\d+), zOrder: \d+ -> (\d+)')
LC = re.compile(r'(ForegroundLifecycle|BackgroundLifecycle) (\S+)')
QUIET_S = 5.0
VIS = re.compile(r'\[G2\.14as-VIS\] dump after RESUMED\+300ms: token=(\S+) .*?mFinished=(\w+) mWindowAdded=(\w+) .*?lifecycleState=(\d+)')


def scan(run):
    t = templates.extract(run)
    pids, pkg = set(t['app_pids']), t['pkg']
    out = {'windows': [], 'z': {}, 'lifecycle': [], 'terminate': 0, 'vis': {}, 'last_lifecycle_ts': None}
    pending = None
    for line in open(Path(run) / 'hilog.txt', errors='replace'):
        m = templates.LINE.match(line)
        if not m:
            continue
        ts = templates.epoch(m.groups(), 2026)
        if t['start'] is None or ts < t['start'] or ts > t['cutoff']:
            continue
        msg, pid = m.group(11), int(m.group(7))
        if pid in pids and 'AppSpawnXJava' not in line:
            c = CS.search(msg)
            if c:
                pending = (c.group(1), int(c.group(2)))
            o = OK.search(msg)
            if o and pending:
                out['windows'].append({'session': int(o.group(1)), 'ability': pending[0], 'androidType': pending[1]})
                pending = None
            if 'finishActivity: OH TerminateAbility' in msg:
                out['terminate'] += 1
            v = VIS.search(msg)
            if v:
                out['vis'][v.group(1)] = f'finished={v.group(2)} windowAdded={v.group(3)} lifecycleState={v.group(4)}'
        z = ZO.search(msg)
        if z:
            out['z'][int(z.group(1))] = int(z.group(2))
        lc = LC.search(msg)
        if lc and pkg in lc.group(2):
            out['lifecycle'].append((lc.group(1)[:3], lc.group(2).split('/')[-1]))
            out['last_lifecycle_ts'] = ts
    out['cutoff'] = t['cutoff']
    return t, out


def features(out):
    types = [w['androidType'] for w in out['windows']]
    dialog_first = 2 in types and 1 in types and types.index(2) < types.index(1)
    last = {}
    for kind, ab in out['lifecycle']:
        last[ab] = kind
    fg_abilities = {ab for kind, ab in out['lifecycle'] if kind == 'For'}
    caller_bg = len(fg_abilities) >= 2 and all(last.get(a) == 'Bac' for a in fg_abilities) and out['terminate'] > 0
    # stable: no lifecycle event in the last QUIET_S before the cutoff (a churning Splash<->X loop that is cut by the
    # hilog end, like fd-organicmaps' 6 terminates, may well re-foreground after it)
    quiet = (out['cutoff'] - out['last_lifecycle_ts']) if out['last_lifecycle_ts'] else 0
    return {'dialog_before_main': dialog_first, 'caller_left_background': caller_bg,
            'caller_left_background_stable': caller_bg and quiet >= QUIET_S, 'quiet_s': round(quiet, 1)}


def apk(key):
    return next(r['path'] for r in b10.inputs(lab_paths.workspaces()) if r['key'] == key)


def tool(name):
    found = sorted((Path.home() / 'Library/Android/sdk/build-tools').glob(f'*/{name}'))
    return str(found[-1]) if found else name


def dex_method(apk_path, sig, n=14):
    """First n instruction lines of the method whose dexdump header contains sig."""
    dd = tool('dexdump')
    with zipfile.ZipFile(apk_path) as z:
        names = [x for x in z.namelist() if x.startswith('classes') and x.endswith('.dex')]
        tmp = HERE / '.dex-tmp'
        tmp.mkdir(exist_ok=True)
        for nm in names:
            p = tmp / nm
            p.write_bytes(z.read(nm))
            text = subprocess.run([dd, '-d', str(p)], capture_output=True, text=True, errors='replace').stdout
            p.unlink()
            lines = text.splitlines()
            for i, l in enumerate(lines):
                if sig in l and '|[' in l:
                    body = [x.split('|', 1)[1] for x in lines[i + 1:i + 1 + n] if '|' in x]
                    tmp.rmdir()
                    return [l.split('|', 1)[1]] + body
        tmp.rmdir()
    return []


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'evidence.txt'))
    a = ap.parse_args()
    groups = population.groups()
    runs = {k: (g, v, r) for k, g, v, r in groups}
    lit_rate = {}
    feats = {}
    for k, g, v, run in groups:
        t, out = scan(run)
        feats[k] = (g, features(out))
        if g == 'LIT':
            for scope in ('app', 'sys'):
                for tpl in t[scope]:
                    lit_rate[(scope, tpl)] = lit_rate.get((scope, tpl), 0) + 1
    nW = sum(1 for g, _ in feats.values() if g == 'WHITE')
    nL = sum(1 for g, _ in feats.values() if g == 'LIT')
    log = [f'# white {nW} / lit {nL} signing runs']
    for name in ('dialog_before_main', 'caller_left_background', 'caller_left_background_stable'):
        w = [k for k, (g, f) in feats.items() if g == 'WHITE' and f[name]]
        l = [k for k, (g, f) in feats.items() if g == 'LIT' and f[name]]
        log.append(f'{name}: white {len(w)}/{nW} {w}; lit {len(l)}/{nL} {l}')
    for key in KEYS:
        g, v, run = runs[key]
        t, out = scan(run)
        log.append(f'\n===== {key}  signed {v}  run {run.replace(str(lab_paths.workspaces()), "$WORKSPACES")}')
        rare = [(s, x) for s in ('app', 'sys') for x in t[s] if lit_rate.get((s, x), 0) <= 3]
        log.append(f'rare templates (in <= 3/117 lit runs): app {sum(s == "app" for s, _ in rare)}, sys {sum(s == "sys" for s, _ in rare)}')
        for s, x in [r for r in rare if r[1][:2] in ('E ', 'W ', 'F ')][:8]:
            log.append(f'    {s} {x[:150]}')
        proof = static_proof.replay(run)
        outcome = {}
        for lk in proof['lookups']:
            outcome.setdefault(lk['session'], []).append(lk['outcome'])
        for w in out['windows']:
            log.append(f"window session {w['session']} androidType={w['androidType']} ({'Activity base' if w['androidType'] == 1 else 'Dialog/TYPE_APPLICATION' if w['androidType'] == 2 else 'other'}) "
                       f"zOrder={out['z'].get(w['session'])} lookups={outcome.get(w['session'], [])}")
        log.append('lifecycle: ' + ' > '.join(f'{k}:{ab.split(".")[-1]}' for k, ab in out['lifecycle']) + f"; TerminateAbility x{out['terminate']}")
        for tok, s in out['vis'].items():
            log.append(f'VIS token {tok}: {s}')
        f = vrt.features(run)
        log.append(f"view tree: dumps {f['vrt_dumps']} views {f['max_views']} content_leaves {f['content_leaves']} text {f['text_views']} :: {f['roots'][:120]}")
        rs = sum(n for k2, n in t['sys'].items() if 'DealWithSurfaceRotationAndGravity' in k2)
        ff = sum(n for k2, n in t['app'].items() if 'activityResumed (first-frame)' in k2)
        log.append(f'render: RS composed-buffer lines {rs}; first-frame markers {ff}; features {feats[key][1]}')
    log.append('\n===== static: itsdicey DiceView.onDraw prologue')
    log += ['    ' + x[:140] for x in dex_method(apk('cv2-com-emmanuelmess-itsdicey'), 'DiceView.onDraw:(Landroid/graphics/Canvas;)V', 5)]
    x = subprocess.run([tool('aapt2'), 'dump', 'xmltree', apk('cv2-com-emmanuelmess-itsdicey'), '--file', 'res/layout/content_main.xml'],
                       capture_output=True, text=True).stdout
    log.append('    content_main.xml TextView visibility attr: ' + str(re.findall(r'visibility\(0x010100dc\)=(\d+)', x)) + ' (2 = gone)')
    log.append('===== static: fd-mobile (Jellyfin) outdated-WebView dialog')
    log += ['    ' + x[:140] for x in dex_method(apk('fd-mobile'), 'WebViewFragment.showOutdatedWebViewDialog', 4)]
    Path(a.out).write_text('\n'.join(log) + '\n')
    print('\n'.join(log))
    return 0


if __name__ == '__main__':
    sys.exit(main())
