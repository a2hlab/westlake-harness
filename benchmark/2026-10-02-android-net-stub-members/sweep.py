#!/usr/bin/env python3
"""Rank the android.net stub-member gaps by how many of the 166 signed U9 keys reference them, before and after the patch.

    sweep.py --before <deployed stubs.jar> --after <patched stubs.jar> --out <dir>

For every key in benchmark/2026-10-01-u9-sweep/outer-signoff.json, the key's APK(s) (same roots as the service-gap
scanner: ~/a2hlab/app-inputs/<key>, $WORKSPACES/westlake-inputs/corpus-v2/app-inputs/<key>) are scanned with
stub_member_gap.scan against each jar; only android.net.* rows are kept. Writes
  members.csv  member, apps referencing it, apps with a call site not caught locally, in members.tsv?, left after
  apps.csv     key, U9 verdict, android.net members referenced / not caught locally, before and after
"""
import argparse
import collections
import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
sys.path.insert(0, str(REPO / 'benchmark/2026-10-02-toutiao-wall3-prediction'))
import lab_paths  # noqa: E402
import stub_member_gap as smg  # noqa: E402

ROOTS = (Path.home() / 'a2hlab/app-inputs', lab_paths.inputs() / 'corpus-v2/app-inputs')
SIGNOFF = REPO / 'benchmark/2026-10-01-u9-sweep/outer-signoff.json'


def apks(key):
    for root in ROOTS:
        found = sorted((root / key).glob('*.apk')) if (root / key).is_dir() else []
        if found:
            return found
    return []


def net_rows(paths, stubs):
    rows = {}
    for apk in paths:
        for r in smg.scan(str(apk), stubs):
            if r['class'].startswith('Landroid/net/') and r['verdict'] == 'missing':
                key = (r['class'], r['member'])
                rows.setdefault(key, set()).update(g for _, _, g in r['sites'])
    return rows   # (class, member) -> set of guards seen at its call sites


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--before', required=True)
    ap.add_argument('--after', required=True)
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    keys = json.loads(SIGNOFF.read_text())['keys']
    before, after = smg.load_stubs([args.before]), smg.load_stubs([args.after])
    listed = {tuple(l.split('\t')[1:3]) for l in (HERE / 'members.tsv').read_text().splitlines()
              if l.startswith('member\t')}
    refs, unguarded, left = collections.Counter(), collections.Counter(), collections.Counter()
    app_rows, missing_apk = [], []
    for key in sorted(keys):
        paths = apks(key)
        if not paths:
            missing_apk.append(key)
            continue
        b, a = net_rows(paths, before), net_rows(paths, after)
        for m, guards in b.items():
            refs[m] += 1
            if guards - {'catches-error'}:
                unguarded[m] += 1
        for m in a:
            left[m] += 1
        app_rows.append([key, keys[key]['verdict'], len(b), sum(1 for g in b.values() if g - {'catches-error'}),
                         len(a), sum(1 for g in a.values() if g - {'catches-error'})])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / 'members.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['class', 'member', 'apps_referencing', 'apps_not_caught_locally', 'in_patch', 'apps_left_after'])
        for m in sorted(refs, key=lambda m: (-refs[m], m)):
            w.writerow([m[0], m[1], refs[m], unguarded[m], m in listed, left[m]])
    with open(out / 'apps.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['key', 'u9_verdict', 'net_members_before', 'net_members_not_caught_before',
                    'net_members_after', 'net_members_not_caught_after'])
        w.writerows(sorted(app_rows, key=lambda r: (-r[3], r[0])))
    print(f'{len(app_rows)} keys scanned ({len(missing_apk)} without an APK here: {", ".join(missing_apk) or "-"}); '
          f'{len(refs)} distinct android.net members missing before, {len(left)} after; '
          f'{sum(1 for r in app_rows if r[2])} keys reference at least one before, {sum(1 for r in app_rows if r[4])} after')
    return 0


if __name__ == '__main__':
    sys.exit(main())
