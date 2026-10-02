#!/usr/bin/env python3
"""Join upstream A2OH/westlake-harness origin/master outcomes + blockers ledger with our 166 signed U9 keys, by package.

    build_map.py [--ref origin/master] [--out <dir>]

Upstream side (read with `git show <ref>:...`, nothing copied by hand):
  benchmark/loop-outcomes.json                 201 apps, first/after at their framework 68
  benchmark/2026-09-28-batch16-20-blind/...    100 apps, draws / past_splash
  benchmark/2026-09-29-top-apps-blind/...       30 apps, outcome / first_blocker
  benchmark/blockers-ledger.json               102 rows app/row/symptom/fixed_in (westlake runtime commits)
  short name -> package: every apps.json / downloads.lock.json and maps/<name>/gap-map.json on the ref, plus the
  corpus-2/3 maps/<package>/ directories and ALIASES below (loop-1 apps named like our keys; marked by_name).
Our side: benchmark/2026-10-01-u9-sweep/outer-signoff.json (verdict), .../u9-first-wall.json (first fatal),
benchmark/2026-10-01-u10-first-wall/u10-first-wall.json, benchmark/2026-10-01-u8-death-clusters/no-fatal-terminations.json,
the key's own manifest package (benchmark/2026-10-02-own-provider-local/provider-census.csv) and its APK sha256.
Writes overlap.csv (one row per our key) and match.json (the joined records walls.csv is built from).
"""
import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'benchmark/2026-10-02-android-net-stub-members'))
import sweep  # noqa: E402  (apks(key): the same key -> APK roots as the service-gap scanner)

# names whose package is not recorded on the ref: corpus-2/3 entries are confirmed by their maps/<package>/ dir,
# loop-1 entries are matched by app name to our key of the same app (by_name)
ALIASES = {
    'breezyweather': 'org.breezyweather', 'element': 'im.vector.app', 'fennec': 'org.mozilla.fennec_fdroid',
    'fluffychat': 'chat.fluffy.fluffychat', 'gallery': 'org.fossify.gallery', 'keepassdx': 'com.kunzisoft.keepass.libre',
    'organicmaps': 'app.organicmaps', 'thunderbird': 'net.thunderbird.android', 'tusky': 'com.keylesspalace.tusky',
    'vlc-fdroid': 'org.videolan.vlc',
    'davx5': 'at.bitfire.davdroid', 'aurorastore': 'com.aurora.store', 'nextcloud': 'com.nextcloud.client',
    'feeder': 'com.nononsenseapps.feeder', 'obtainium': 'dev.imranr.obtainium.fdroid', 'fairemail': 'eu.faircode.email',
    'catima': 'me.hackerchick.catima', 'osmand': 'net.osmand.plus', 'musicplayer': 'org.fossify.musicplayer',
    'jellyfin': 'org.jellyfin.mobile',
}
BY_NAME = {'aegis': 'com.beemdevelopment.aegis', 'anki': 'com.ichi2.anki', 'antennapod': 'de.danoeh.antennapod',
           'markor': 'net.gsantner.markor', 'mindustry': 'io.anuke.mindustry', 'newpipe': 'org.schabi.newpipe',
           'ooniprobe': 'org.openobservatory.ooniprobe', 'opencamera': 'net.sourceforge.opencamera',
           'ppsspp': 'org.ppsspp.ppsspp', 'termux': 'com.termux', 'wikipedia': 'org.wikipedia'}


def show(ref, path):
    r = subprocess.run(['git', '-C', str(REPO), 'show', f'{ref}:{path}'], capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


def upstream(ref):
    files = subprocess.run(['git', '-C', str(REPO), 'ls-tree', '-r', '--name-only', ref, 'benchmark'],
                           capture_output=True, text=True).stdout.split()
    name2pkg, name2sha, src = {}, {}, {}
    for f in files:
        if f.endswith('downloads.lock.json') or f.endswith('/apps.json'):
            try:
                d = json.loads(show(ref, f))
            except Exception:
                continue
            for k, v in (d.items() if isinstance(d, dict) else []):
                if isinstance(v, dict) and v.get('package'):
                    name2pkg.setdefault(k, v['package'])
                    src.setdefault(k, f)
                    sha = v.get('sha256') or v.get('base_sha256')
                    if sha:
                        name2sha.setdefault(k, sha)
        m = re.match(r'benchmark/[^/]+/maps/([^/]+)/gap-map\.json$', f)
        if m and m.group(1) not in name2pkg:
            try:
                d = json.loads(show(ref, f))
            except Exception:
                continue
            pkg = d.get('package') if isinstance(d, dict) else None
            if pkg:
                name2pkg[m.group(1)] = pkg
                src[m.group(1)] = f
    for n, p in ALIASES.items():
        name2pkg.setdefault(n, p)
        src.setdefault(n, 'maps/<package> dir on the ref')
    for n, p in BY_NAME.items():
        name2pkg.setdefault(n, p)
        src.setdefault(n, 'by_name')
    loop = json.loads(show(ref, 'benchmark/loop-outcomes.json'))['apps']
    b1620 = json.loads(show(ref, 'benchmark/2026-09-28-batch16-20-blind/outcomes.json'))
    top = json.loads(show(ref, 'benchmark/2026-09-29-top-apps-blind/outcomes.json'))
    ledger = json.loads(show(ref, 'benchmark/blockers-ledger.json'))['blockers']
    apps = {}
    for n, v in loop.items():
        apps[n] = {'set': 'loop-outcomes', 'batch': v.get('batch'), 'first': v.get('first'), 'after': v.get('after')}
    for n, drew in b1620['draws'].items():
        apps.setdefault(n, {'set': 'batch16-20', 'batch': 'batch-16-20', 'first': 'draws' if drew else 'blocked',
                            'after': 'draws' if drew else 'blocked',
                            'past_splash': b1620.get('past_splash', {}).get(n),
                            'excluded': b1620.get('excluded', {}).get(n)})
    for n, v in top.items():
        apps.setdefault(n, {'set': 'top-apps', 'batch': 'top-apps', 'first': v.get('outcome'), 'after': v.get('outcome'),
                            'first_blocker': v.get('first_blocker')})
    rows = defaultdict(list)
    for r in ledger:
        rows[r['app']].append({k: r.get(k) for k in ('row', 'symptom', 'fixed_in', 'corpus')})
    by_pkg = defaultdict(list)
    for n, a in apps.items():
        p = name2pkg.get(n)
        if p:
            by_pkg[p].append(dict(a, name=n, package=p, sha256=name2sha.get(n), pkg_source=src.get(n),
                                  ledger=rows.get(n, [])))
    unmapped = sorted(n for n in apps if n not in name2pkg)
    return by_pkg, unmapped, len(apps), len(ledger)


def ours():
    signoff = json.loads((REPO / 'benchmark/2026-10-01-u9-sweep/outer-signoff.json').read_text())['keys']
    fw = {e['key']: e for e in json.loads((REPO / 'benchmark/2026-10-01-u9-sweep/u9-first-wall.json').read_text())['entries']}
    u10 = {e['key']: e for e in json.loads((REPO / 'benchmark/2026-10-01-u10-first-wall/u10-first-wall.json').read_text())['entries']}
    nf = json.loads((REPO / 'benchmark/2026-10-01-u8-death-clusters/no-fatal-terminations.json').read_text())
    nf_cause = {k: g['cause'] for g in nf['groups'] for k in g['keys']}
    pkgs = {r['key']: r['package'] for r in csv.DictReader(open(REPO / 'benchmark/2026-10-02-own-provider-local/provider-census.csv'))}
    out = {}
    for k, s in signoff.items():
        apk = sweep.apks(k)
        sha = hashlib.sha256(apk[0].read_bytes()).hexdigest() if apk else None
        e, e10 = fw.get(k, {}), u10.get(k, {})
        out[k] = {'key': k, 'package': pkgs.get(k), 'apk_sha256': sha, 'u9_verdict': s['verdict'],
                  'u9_family': e.get('family', ''), 'u9_cause': (e.get('cause') or '')[:300],
                  'u9_first_fatal': (e.get('first_fatal') or '')[:300], 'u8_no_fatal_cause': nf_cause.get(k, ''),
                  'u10_verdict': e10.get('verdict', ''), 'u10_family': e10.get('family', ''),
                  'u10_cause': (e10.get('cause') or '')[:300]}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--ref', default='origin/master')
    ap.add_argument('--out', default=str(HERE))
    args = ap.parse_args()
    by_pkg, unmapped, n_up, n_ledger = upstream(args.ref)
    our = ours()
    records = []
    for k, o in sorted(our.items()):
        ups = by_pkg.get(o['package'], [])
        u = ups[0] if ups else None
        records.append(dict(o, upstream=u, upstream_all=[x['name'] for x in ups],
                            same_apk=(None if not u or not u.get('sha256') or not o['apk_sha256']
                                      else u['sha256'] == o['apk_sha256'])))
    out = Path(args.out)
    (out / 'match.json').write_text(json.dumps({'ref': subprocess.run(['git', '-C', str(REPO), 'rev-parse', args.ref],
                                                                      capture_output=True, text=True).stdout.strip(),
                                                'upstream_apps': n_up, 'ledger_rows': n_ledger,
                                                'unmapped_upstream_names': unmapped, 'records': records},
                                               ensure_ascii=False, indent=1) + '\n')
    with open(out / 'overlap.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['key', 'package', 'u9_verdict', 'upstream_name', 'upstream_set', 'upstream_first', 'upstream_after',
                    'same_apk', 'pkg_match_source', 'our_first_fatal_family', 'our_first_fatal_cause',
                    'upstream_ledger_rows', 'upstream_fixed_in'])
        for r in records:
            u = r['upstream'] or {}
            w.writerow([r['key'], r['package'], r['u9_verdict'], u.get('name', ''), u.get('set', ''), u.get('first', ''),
                        u.get('after', ''), '' if r['same_apk'] is None else r['same_apk'], u.get('pkg_source', ''),
                        r['u9_family'] or (r['u8_no_fatal_cause'] and 'no-fatal'), (r['u9_cause'] or r['u8_no_fatal_cause'])[:200],
                        ' | '.join(f"{x['row']}: {x['symptom']}"[:160] for x in u.get('ledger', [])),
                        ' '.join(sorted({x['fixed_in'] for x in u.get('ledger', []) if x.get('fixed_in')}))])
    matched = [r for r in records if r['upstream']]
    print(f'upstream apps {n_up} (unmapped names {len(unmapped)}), ledger rows {n_ledger}; our keys {len(records)}, '
          f'matched by package {len(matched)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
