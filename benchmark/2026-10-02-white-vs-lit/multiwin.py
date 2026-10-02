#!/usr/bin/env python3
"""Did the Activity that should be on top get a drawable surface?

    multiwin.py <run_dir>...

From the run's hilog, window launch-3 s .. min(t20, hilog end):
  requested   SceneBoard's `OnRequestSceneSession: [<pkg>, <module>, <ability>]` in order (the launcher click first,
              then every ability the app itself starts); top = the LAST requested ability (simple class name)
  surfaces    per `BBQ.create name=VRI[<name>]` (app pid), the outcome of its first surface lookup:
              `ok` (BBQ.update ... OHNativeWindow=), `empty` (BBQ.getSurface: ohNativeWindow null -> empty Surface);
              `rescued_later` if an empty VRI later gets an OHNativeWindow on the same BBQ
  misroute    >= 2 VRIs, and the top ability's VRI got an empty Surface and was never rescued
This is the last-session rescue (DIGEST 2026-10-01 07:51/14:29: getOhNativeWindow answers in the bridge copy that
created the session; the compat shim's fallback only rescues the LAST created session) seen per Activity.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import templates  # noqa: E402

REQ = re.compile(r'OnRequestSceneSession: \[([^,\]]+), ([^,\]]+), ([^\]]+)\]')
CREATE = re.compile(r'BBQ\.create name=VRI\[([^\]]+)\] ptr=(\w+)')
OK = re.compile(r'BBQ\.update: sessionId=(\d+) → OHNativeWindow=')
EMPTY = re.compile(r'BBQ\.getSurface: ohNativeWindow null \(sessionId=(\d+)')


def analyse(run):
    t = templates.extract(run)
    pids, pkg = set(t['app_pids']), t['pkg']
    requested, vris, order = [], {}, []
    last_vri_by_tid = {}
    import datetime as dt
    year = dt.datetime.fromtimestamp(t['cutoff'] or 1.79e9, templates.BOARD_TZ).year
    for line in open(Path(run) / 'hilog.txt', errors='replace'):
        if 'OnRequestSceneSession' not in line and 'BBQ.' not in line:
            continue
        m = templates.LINE.match(line)
        if not m:
            continue
        ts = templates.epoch(m.groups(), year)
        if t['start'] is None or ts < t['start'] or ts > t['cutoff']:
            continue
        msg, pid, tid = m.group(11), int(m.group(7)), m.group(8)
        r = REQ.search(msg)
        if r and r.group(1).strip() == pkg:
            ab = r.group(3).strip().split('.')[-1]
            if not requested or requested[-1] != ab:
                requested.append(ab)
            continue
        if pid not in pids or 'AppSpawnXJava' in line:
            continue
        c = CREATE.search(msg)
        if c:
            name = c.group(1)
            vris[name] = {'first': None, 'rescued_later': False}
            order.append(name)
            last_vri_by_tid[tid] = name
            continue
        cur = last_vri_by_tid.get(tid)
        if cur is None:
            continue
        if OK.search(msg):
            if vris[cur]['first'] is None:
                vris[cur]['first'] = 'ok'
            elif vris[cur]['first'] == 'empty':
                vris[cur]['rescued_later'] = True
        elif EMPTY.search(msg) and vris[cur]['first'] is None:
            vris[cur]['first'] = 'empty'
    top = requested[-1] if requested else None
    top_vri = vris.get(top)
    misroute = (len(vris) >= 2 and top_vri is not None and top_vri['first'] == 'empty' and not top_vri['rescued_later'])
    return {'requested': requested, 'top': top, 'vris': order,
            'outcomes': {k: v['first'] + ('+rescued' if v['rescued_later'] else '') if v['first'] else 'none'
                         for k, v in vris.items()},
            'top_outcome': (top_vri['first'] if top_vri else 'no-vri'), 'misroute': misroute}


if __name__ == '__main__':
    for a in sys.argv[1:]:
        print(Path(a).name, analyse(a))
