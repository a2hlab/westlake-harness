#!/usr/bin/env python3
"""The app's own view tree as the runtime's G2.14as probe dumped it (LifecycleAdapter.java, `[G2.14as-VRT]`, depth 8,
at RESUMED+1500 ms and +5000 ms), per Activity: the last complete dump before the cutoff.

    vrt.py <run_dir>...

Each node: depth, class (simple name), DL (RenderNode.hasDisplayList), w x h, visibility. Content features (per run,
over every Activity's last tree):
  webview_full    a visible node whose class contains "WebView" covering >= half the screen
  surface_full    a visible SurfaceView / GLSurfaceView / GLView / TextureView covering >= half the screen
  content_leaves  visible leaves (no deeper child) under ContentFrameLayout/`content` with a non-zero size
  max_views       the largest tree size among the run's Activities
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import templates  # noqa: E402

NODE = re.compile(r'^(\.*)([\w$.]+)\{DL=([TF]) mem=\d+ (\d+)x(\d+) v=(\d+)')
HEAD = re.compile(r'\[T=(\d+)ms\]\[G2\.14as-VRT\] tree')
SCREEN = 1200 * 1920


def trees(run):
    """{activity_token_or_index: [nodes]} -- the last VRT dump per dumping thread sequence (two Activities dump
    interleaved by timepoint; a dump is the run of VRT lines after a `tree` header)."""
    t = templates.extract(run)
    pids, cutoff, start = set(t['app_pids']), t['cutoff'], t['start']
    dumps, cur = [], None
    year = None
    for line in open(Path(run) / 'hilog.txt', errors='replace'):
        if 'AppSpawnXJava' in line or 'G2.14as-VRT' not in line:
            continue
        m = templates.LINE.match(line)
        if not m or int(m.group(7)) not in pids:
            continue
        if year is None:
            import datetime as dt
            year = dt.datetime.fromtimestamp(cutoff or 1.79e9, templates.BOARD_TZ).year
        ts = templates.epoch(m.groups(), year)
        if cutoff and ts > cutoff:
            break
        msg = m.group(11)
        h = HEAD.search(msg)
        if h:
            cur = {'t': int(h.group(1)), 'tid': m.group(8), 'nodes': []}
            dumps.append(cur)
            continue
        body = msg.split('[G2.14as-VRT]', 1)[1].strip()
        n = NODE.match(re.sub(r'@[0-9a-f]+', '', body))
        if n and cur is not None:
            cur['nodes'].append({'depth': len(n.group(1)) // 2, 'cls': n.group(2), 'dl': n.group(3) == 'T',
                                 'w': int(n.group(4)), 'h': int(n.group(5)), 'v': int(n.group(6)),
                                 'text': 'text=' in body})
    return dumps


def features(run):
    dumps = trees(run)
    if not dumps:
        return {'vrt_dumps': 0, 'webview_full': 0, 'surface_full': 0, 'content_leaves': 0, 'max_views': 0, 'text_views': 0,
                'roots': ''}
    # the last dump of each distinct root shape (Activities dump alternately at the same timepoints)
    last_t = max(d['t'] for d in dumps)
    final = [d for d in dumps if d['t'] == last_t] or dumps[-1:]
    wv = sf = leaves = txt = 0
    for d in final:
        nodes = d['nodes']
        for i, nd in enumerate(nodes):
            big = nd['v'] == 0 and nd['w'] * nd['h'] >= SCREEN // 2
            if big and 'WebView' in nd['cls']:
                wv += 1
            if big and re.search(r'SurfaceView|GLView|TextureView', nd['cls']):
                sf += 1
            is_leaf = i + 1 >= len(nodes) or nodes[i + 1]['depth'] <= nd['depth']
            if is_leaf and nd['v'] == 0 and nd['w'] * nd['h'] > 0 and nd['depth'] >= 5:
                leaves += 1
            txt += nd['text'] and nd['v'] == 0
    return {'vrt_dumps': len(dumps), 'webview_full': wv, 'surface_full': sf, 'content_leaves': leaves,
            'max_views': max(len(d['nodes']) for d in final), 'text_views': txt,
            'roots': ' | '.join('>'.join(n['cls'] for n in d['nodes'] if n['depth'] in (5, 6, 7))[:120] for d in final)}


if __name__ == '__main__':
    for a in sys.argv[1:]:
        print(Path(a).name, features(a))
