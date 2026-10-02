#!/usr/bin/env python3
"""Per-run hilog message templates, cut at min(t20, hilog end): the unit both the pair diff and the population
rates count.

    templates.py <run_dir>...            # print a summary per run (cache in $WVL_CACHE or <scratch>)

A run dir is a bms_batch key directory (record.json, hilog.txt, processes-t5/t20.txt). Window:
  start  = the first `nativeOnScheduleLaunchApplication ENTRY bundle=<pkg>` line minus 3 s (the launcher click, the
           SceneBoard session and appspawn lines fall inside it);
  cutoff = min(board mtime of t20.jpeg (record.json remote_stat), last hilog line) -- the captured hilog ends 4-7 s
           before t20 (DIGEST 2026-10-02), so a template is only "absent at t20" if absent before the cutoff.
class_linker debug lines become `CLS <class>` and OH_RegHook lines `REG <class>` (which code ran).
Scope: `app` = lines whose pid is the app's (binding pids + the bms uid's pids in processes-t5/t20); `sys` = every
other pid in the window. Template = level + tag + message with hex, numbers, the package name and paths' digits
normalised (`norm`); counts are kept but the analyses use presence.
"""
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import first_fatal  # noqa: E402
import lab_paths  # noqa: E402

BOARD_TZ = dt.timezone(dt.timedelta(hours=8))
LINE = re.compile(r'^(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d)\.(\d{3})\s+(\d+)\s+(\d+)\s+([VDIWEF])\s+([^:]*?):\s?(.*)$')
HEX = re.compile(r'\b0x[0-9a-fA-F]+\b|\b[0-9a-fA-F]{6,}\b')
NUM = re.compile(r'-?\d+(?:\.\d+)?')
SPACE = re.compile(r'\s+')
TRACE = re.compile(r'^\[[0-9a-fA-F]+, [0-9a-fA-F]+, [0-9a-fA-F]+\]\s*')   # hitrace id prefix, present or not per line
START_SLACK = 3.0
VERSION = 4   # bump when norm/window changes (invalidates the cache)


def cache_dir():
    d = Path(os.environ.get('WVL_CACHE') or (lab_paths.inputs() / 'cache/white-vs-lit'))
    d.mkdir(parents=True, exist_ok=True)
    return d


KLASS = re.compile(r'\bklass=(\S+)')
REGHOOK = re.compile(r'^(\S+?)::')


def norm(msg, pkg, tag=''):
    """class_linker debug lines collapse to the class they link (`CLS <class>`), OH_RegHook lines to the Java class
    whose natives are bound (`REG <class>`): which code ran, not the per-line details."""
    msg = TRACE.sub('', msg)
    if '[class_linker.cc' in msg:
        k = KLASS.search(msg)
        return ('CLS ' + (k.group(1).replace(pkg, '<PKG>') if pkg else k.group(1))) if k else None
    if tag.endswith('OH_RegHook'):
        k = REGHOOK.search(msg)
        return ('REG ' + k.group(1)) if k else None
    msg = TRACE.sub('', msg)
    m = msg.replace(pkg, '<PKG>') if pkg else msg
    m = HEX.sub('<H>', m)
    m = NUM.sub('<N>', m)
    return SPACE.sub(' ', m).strip()[:200]


def epoch(groups, year):
    mo, d, h, mi, s, ms = (int(x) for x in groups[:6])
    return dt.datetime(year, mo, d, h, mi, s, ms * 1000, tzinfo=BOARD_TZ).timestamp()


def t20_epoch(rec):
    for s in rec.get('screenshots', []):
        if Path(s.get('path', '')).name == 't20.jpeg' and s.get('remote_stat'):
            return float(s['remote_stat'].split()[1])
    return None


def app_pids(run, rec):
    pids = set()
    uid = (rec.get('bms') or {}).get('uid')
    if uid:
        for n in ('processes-t5.txt', 'processes-t20.txt'):
            pids |= first_fatal.processes(run / n, uid) or set()
    return pids


def extract(run):
    """{'key','pkg','start','cutoff','cut_by','app_pids','lines_app','lines_sys','app': {tpl: n}, 'sys': {tpl: n}}"""
    run = Path(run)
    hl = run / 'hilog.txt'
    raw = hl.read_bytes()
    tag = hashlib.sha256(raw).hexdigest()[:16]
    cf = cache_dir() / f'{run.name}-{tag}-v{VERSION}.json'
    if cf.exists():
        return json.loads(cf.read_text())
    rec = json.loads((run / 'record.json').read_text())
    pkg = rec.get('package', '')
    t20 = t20_epoch(rec)
    year = dt.datetime.fromtimestamp(t20 or rec.get('screenshots', [{}])[0].get('captured_at') or 1.79e9, BOARD_TZ).year
    lines = raw.decode(errors='replace').splitlines()
    parsed, pids, bind_t = [], app_pids(run, rec), None
    needle = f'nativeOnScheduleLaunchApplication ENTRY bundle={pkg} '
    for line in lines:
        m = LINE.match(line)
        if not m:
            continue
        g = m.groups()
        t = epoch(g, year)
        parsed.append((t, int(g[6]), g[8], g[9].strip(), g[10]))
        if needle in line:
            pids.add(int(g[6]))
            bind_t = t if bind_t is None else min(bind_t, t)
    end = max((p[0] for p in parsed), default=None)
    cutoff = min(x for x in (t20, end) if x is not None) if (t20 or end) else None
    cut_by = 't20' if t20 is not None and end is not None and t20 <= end else 'hilog-end'
    start = (bind_t - START_SLACK) if bind_t is not None else None
    out = {'key': run.name, 'pkg': pkg, 'start': start, 'cutoff': cutoff, 'cut_by': cut_by, 'bind_t': bind_t,
           'app_pids': sorted(pids), 'app': {}, 'sys': {}, 'lines_app': 0, 'lines_sys': 0}
    if start is not None:
        for t, pid, lvl, tg, msg in parsed:
            if t < start or t > cutoff:
                continue
            scope = 'app' if pid in pids else 'sys'
            n = norm(msg, pkg, tg)
            if n is None:
                continue
            k = n if n.startswith(('CLS ', 'REG ')) else f'{lvl} {tg}: {n}'
            out[scope][k] = out[scope].get(k, 0) + 1
            out['lines_' + scope] += 1
    cf.write_text(json.dumps(out))
    return out


if __name__ == '__main__':
    for a in sys.argv[1:]:
        r = extract(a)
        print(r['key'], 'bind' if r['bind_t'] else 'NO-BIND', f"window {r['cutoff'] - r['start']:.1f}s" if r['start'] else '',
              r['cut_by'], 'app tpl', len(r['app']), 'sys tpl', len(r['sys']), 'app lines', r['lines_app'])
