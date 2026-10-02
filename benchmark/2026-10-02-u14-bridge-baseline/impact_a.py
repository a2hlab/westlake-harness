#!/usr/bin/env python3
"""Which of the 166 keys reach the class-a (intended) new bridge paths, and do their Java peers exist?

    impact_a.py [--out impact-a.csv]

1) [APK-ORIENTATION] (master ability_scheduler_adapter.cpp ScheduleAbilityTransaction -> parent MainSession
   orientation from the manifest): per key, the LAUNCHER activity's android:screenOrientation (aapt2 xmltree of
   the frozen APK, B10 collect.inputs). A non-portrait/unspecified value means the new path changes the session
   orientation.
2) [OH-DISPLAY-EVENT] (display_manager_adapter_jni.cpp framework copy): every key that initialises
   DisplayManagerGlobal reaches RegisterDisplayListener; the Java side dispatches only if the runtime projection
   class exists.
3) Java peers: adapter.activity.DisplayManagerProjectionProxy, adapter.activity.ManifestOrientationProjection,
   adapter.activity.CapybaraLetterboxProjection -- present in the U13 runtime jar 0482c9b1 / BCP framework jar
   2257b835 (the jars U14 would run with)?
"""
import argparse
import csv
import re
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
sys.path.insert(0, str(REPO / 'benchmark/2026-10-01-b10-theme-graphics'))
sys.path.insert(0, str(REPO / 'benchmark/2026-10-02-toutiao-oldroute-diff'))
import collect  # noqa: E402
import java_classes  # noqa: E402
import lab_paths  # noqa: E402

ORIENT = {0: 'landscape', 1: 'portrait', 2: 'user', 3: 'behind', 4: 'sensor', 5: 'nosensor', 6: 'sensorLandscape',
          7: 'sensorPortrait', 8: 'reverseLandscape', 9: 'reversePortrait', 10: 'fullSensor', 11: 'userLandscape',
          12: 'userPortrait', 13: 'fullUser', 14: 'locked', -1: 'unspecified'}
LANDSCAPE = {0, 6, 8, 11}


def aapt2():
    found = sorted((Path.home() / 'Library/Android/sdk/build-tools').glob('*/aapt2'))
    return str(found[-1])


def launcher_orientation(apk):
    x = subprocess.run([aapt2(), 'dump', 'xmltree', apk, '--file', 'AndroidManifest.xml'], capture_output=True,
                       text=True, errors='replace').stdout
    # split into element blocks; an activity/activity-alias block owns the attributes until the next E:
    acts, cur = [], None
    for line in x.splitlines():
        m = re.match(r'^(\s*)E: (\S+)', line)
        if m:
            depth, tag = len(m.group(1)), m.group(2)
            if tag in ('activity', 'activity-alias'):
                cur = {'depth': depth, 'orient': None, 'launcher': False, 'name': None}
                acts.append(cur)
            elif cur is not None and depth <= cur['depth']:
                cur = None
            continue
        if cur is None:
            continue
        if 'screenOrientation(0x0101001e)' in line:
            v = re.search(r'=(?:\(type 0x10\))?(0x[0-9a-f]+|-?\d+)', line)
            if v:
                cur['orient'] = int(v.group(1), 0)
        if 'android.intent.category.LAUNCHER' in line:
            cur['launcher'] = True
        if 'android:name(0x01010003)' in line and cur['name'] is None:
            n = re.search(r'="([^"]+)"', line)
            cur['name'] = n.group(1) if n else None
    launchers = [a for a in acts if a['launcher']]
    return launchers[0] if launchers else None


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'impact-a.csv'))
    a = ap.parse_args()
    gen = lab_paths.inputs() / 'generations'
    jars = {'runtime 0482c9b1': gen / 'u12r2-v1/oh-adapter-runtime-u12r2.jar',
            'framework 2257b835': gen / 't8-rebake-effective/jars9/oh-adapter-framework.jar'}
    peers = ['Ladapter/activity/DisplayManagerProjectionProxy;', 'Ladapter/activity/ManifestOrientationProjection;',
             'Ladapter/activity/CapybaraLetterboxProjection;']
    for name, j in jars.items():
        defs = java_classes.jar_defined(Path(j).read_bytes())
        print(f'{name}: ' + ', '.join(f'{p.split("/")[-1][:-1]}={"yes" if p in defs else "no"}' for p in peers))
    rows = []
    for r in collect.inputs(lab_paths.workspaces()):
        act = launcher_orientation(r['path'])
        o = act['orient'] if act and act['orient'] is not None else -1
        rows.append({'key': r['key'], 'launcher': (act or {}).get('name') or '', 'screenOrientation': ORIENT.get(o, str(o)),
                     'orientation_path_changes_session': o in LANDSCAPE})
    with open(a.out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print('launcher screenOrientation over', len(rows), 'keys:', dict(Counter(r['screenOrientation'] for r in rows)))
    print('landscape launchers:', [r['key'] for r in rows if r['orientation_path_changes_session']])
    return 0


if __name__ == '__main__':
    sys.exit(main())
