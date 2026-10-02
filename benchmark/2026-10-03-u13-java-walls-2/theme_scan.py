#!/usr/bin/env python3
"""Static check behind the fd-api probe: is fd-api's launch theme an unusual resource shape that lit apps do not have?

    theme_scan.py [--out theme-scan.csv]

Per frozen APK: the launcher activity (activity-alias -> its targetActivity) theme, else the application theme;
then, from `aapt2 dump resources`, that style's DEFAULT-configuration entry: its attribute count (`size=`) and parent,
followed up the parent chain (default configs) until a framework/absent parent. Recorded:
  theme, default_size (attributes in the launch style's own default bag), chain (style names), chain_len,
  reaches_appcompat (a Theme.AppCompat* / Theme.MaterialComponents* style is on the chain),
  has_window_action_bar (some bag on the chain defines the app attr windowActionBar).
Joined with the U10.1T8 verdict (white-vs-lit population) where the key has one.
"""
import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
sys.path.insert(0, str(REPO / 'benchmark/2026-10-01-b10-theme-graphics'))
sys.path.insert(0, str(REPO / 'benchmark/2026-10-02-white-vs-lit'))
import collect  # noqa: E402
import lab_paths  # noqa: E402
import population  # noqa: E402

AAPT2 = str(sorted((Path.home() / 'Library/Android/sdk/build-tools').glob('*/aapt2'))[-1])


def manifest_theme(apk):
    x = subprocess.run([AAPT2, 'dump', 'xmltree', apk, '--file', 'AndroidManifest.xml'], capture_output=True,
                       text=True, errors='replace').stdout
    elems, cur = [], None
    for line in x.splitlines():
        m = re.match(r'^(\s*)E: (\S+)', line)
        if m:
            cur = {'tag': m.group(2), 'depth': len(m.group(1)), 'attrs': {}, 'launcher': False}
            elems.append(cur)
            continue
        a = re.match(r'\s*A: http://schemas.android.com/apk/res/android:(\w+)\(0x[0-9a-f]+\)=(.*)$', line)
        if a and cur is not None:
            cur['attrs'][a.group(1)] = a.group(2)
        if 'android.intent.category.LAUNCHER' in line:
            # attribute the LAUNCHER category to the nearest enclosing activity / alias
            for e in reversed(elems):
                if e['tag'] in ('activity', 'activity-alias'):
                    e['launcher'] = True
                    break
    def val(s):
        m = re.search(r'@0x([0-9a-f]+)', s or '')
        return int(m.group(1), 16) if m else None
    def name(s):
        m = re.match(r'"([^"]+)"', s or '')
        return m.group(1) if m else None
    app = next((e for e in elems if e['tag'] == 'application'), {'attrs': {}})
    acts = {name(e['attrs'].get('name')): e for e in elems if e['tag'] == 'activity'}
    for e in elems:
        if e['tag'] in ('activity', 'activity-alias') and e['launcher']:
            if e['tag'] == 'activity-alias':
                tgt = acts.get(name(e['attrs'].get('targetActivity')))
                t = val((tgt or {}).get('attrs', {}).get('theme')) if tgt else None
                return t or val(e['attrs'].get('theme')) or val(app['attrs'].get('theme'))
            return val(e['attrs'].get('theme')) or val(app['attrs'].get('theme'))
    return val(app['attrs'].get('theme'))


def styles(apk):
    out = subprocess.run([AAPT2, 'dump', 'resources', apk], capture_output=True, text=True, errors='replace').stdout
    res, cur = {}, None
    for line in out.splitlines():
        m = re.match(r'\s*resource 0x([0-9a-f]+) style/(\S+)', line)
        if m:
            cur = res.setdefault(int(m.group(1), 16), {'name': m.group(2), 'default': None, 'attrs': []})
            continue
        if re.match(r'\s*resource ', line):
            cur = None
            continue
        if cur is None:
            continue
        m = re.match(r'\s*\(\) \(style\) size=(\d+)(?: parent=\S+ \(0x([0-9a-f]+)\))?', line)
        if m:
            cur['default'] = (int(m.group(1)), int(m.group(2), 16) if m.group(2) else None)
            cur['in_default'] = True
            continue
        if re.match(r'\s*\(\S+\) \(style\)', line):
            cur['in_default'] = False
            continue
        if cur.get('in_default'):
            a = re.match(r'\s*(\w+)\(0x', line)
            if a:
                cur['attrs'].append(a.group(1))
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'theme-scan.csv'))
    a = ap.parse_args()
    verdict = {k: g for k, g, v, run in population.groups()}
    rows = []
    for r in collect.inputs(lab_paths.workspaces()):
        t = manifest_theme(r['path'])
        row = {'key': r['key'], 'group': verdict.get(r['key'], ''), 'theme': f'{t:#x}' if t else '',
               'default_size': '', 'chain_len': 0, 'reaches_appcompat': False, 'has_window_action_bar': False, 'chain': ''}
        if t and (t >> 24) == 0x7f:
            st = styles(r['path'])
            chain, sid, first = [], t, True
            while sid in st and len(chain) < 40:
                s = st[sid]
                chain.append(s['name'])
                if s['default'] is None:
                    break
                if first:
                    row['default_size'] = s['default'][0]
                    first = False
                if 'windowActionBar' in s['attrs']:
                    row['has_window_action_bar'] = True
                sid = s['default'][1]
            row['chain'] = ' > '.join(chain)
            row['chain_len'] = len(chain)
            row['reaches_appcompat'] = any(n.startswith(('Theme.AppCompat', 'Base.Theme.AppCompat',
                                                         'Theme.MaterialComponents', 'Base.Theme.MaterialComponents',
                                                         'Theme.Material3', 'Base.V')) for n in chain)
        rows.append(row)
    with open(a.out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    app = [r for r in rows if r['reaches_appcompat']]
    zero = [r for r in app if r['default_size'] == 0]
    print(f'keys {len(rows)}; launch theme reaches AppCompat/MaterialComponents {len(app)}; '
          f'of those the launch style\'s default bag is EMPTY (size=0, parent only) {len(zero)}')
    from collections import Counter
    print('  empty-bag keys by U10.1T8 group:', dict(Counter(r['group'] or 'no-verdict' for r in zero)))
    for r in zero:
        print('   ', r['key'], r['group'] or '-', r['theme'], r['chain'][:150])
    return 0


if __name__ == '__main__':
    sys.exit(main())
