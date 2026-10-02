#!/usr/bin/env python3
"""Every file the old Toutiao route laid down, against the same-named file on today's route-A board.

    inventory.py [--out inventory.csv]

Old side: the delivery bundle $HOME/a2hlab-provision/ttbundle (MANIFEST.sha256, 7 entries) as provision_toutiao.sh
lays it out:
  tt-rt.tar    -> RT = /data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bf...,
                  bind-mounted by source_app_namespace at /data/local/tmp/asx (the paths run.sh uses)
  tt-stage.tar -> /data/local/tmp/a2hlab-app-c91d26bf... (source_app_namespace, host_spawn, request.bin)
  tt-wd.tar    -> /data/local/tmp/operator45/selfheal48 (watchdog, keeper, spawn/start-parent, screen-gate)
  aot/*        -> RT/oat/arm64 (only with --with-aot; the 9-27/28 boards ran Tier-1, without it)
  source-host.hap -> bm install (org.westlake.imehost)
Old loader per file, from run.sh (LD_LIBRARY_PATH / LD_PRELOAD / WESTLAKE_ANDROID_NATIVE_TARGETS / _PRELOAD), the
old appspawn-x open sites (open_site_scan.py: all plain dlopen into the default namespace) and the old child
stderr ([SOURCE-NATIVE-LOAD] lines, 2026-09-25 toutiao run in westlake-harness-touch25).
New side: window5 61b toutiao run (2026-10-02 17:05, runtime d6848fa2c989): runtime-fingerprint.txt (board paths +
SHA), maps-t5-10020.txt (what the process mapped at t5), hilog.txt; plus the APK's own lib/arm64-v8a for app libs.
"""
import argparse
import csv
import hashlib
import io
import json
import re
import sys
import tarfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
sys.path.insert(0, str(REPO / 'benchmark/2026-10-02-android-net-stub-members'))
import lab_paths  # noqa: E402
import sweep  # noqa: E402

WS = lab_paths.workspaces()
BUNDLE = Path.home() / 'a2hlab-provision/ttbundle'
RT_BOARD = '/data/local/tmp/asx'
STAGE_BOARD = '/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d'
WD_BOARD = '/data/local/tmp/operator45/selfheal48'
OLD_STDERR = WS / ('westlake-harness-touch25/benchmark/2026-09-25-touch-factorial/evidence/online-fresh-1/'
                   'child.stderr.gz')
V3 = lab_paths.inputs() / 'generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle'
W5 = WS / ('westlake-harness-u7-executor/benchmark/2026-10-02-u10-1-t8-rerun/window5/u101-t8-A5-20261002T083800/61b/'
           'runner/toutiao-gain/20261002T170518-ad72d00a/61b0657200000000000000000324012c')
# run.sh of the bundle (read from the tar below) names these loader sets
ENV_KEYS = ('LD_PRELOAD', 'WESTLAKE_ANDROID_NATIVE_TARGETS', 'WESTLAKE_ANDROID_NATIVE_PRELOAD',
            'WESTLAKE_PERMISSION_HELPER_PATH', 'WESTLAKE_ACCOUNT_HELPER_PATH', 'WESTLAKE_CONNECTIVITY_HELPER_PATH')
# appspawn-x a7a358c6 open sites (open_site_scan.py, default namespace)
OLD_HOST_OPENS = {'liboh_android_runtime.so', 'liboh_adapter_bridge.so', 'liboh_hwui_shim.so', 'libnet_connection.so',
                  'libsoundpool.so', 'libjnigraphics.so'}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def manifest_ok():
    for line in (BUNDLE / 'MANIFEST.sha256').read_text().splitlines():
        h, name = line.split()
        assert sha((BUNDLE / name).read_bytes()) == h, f'{name} does not match MANIFEST'


def run_env(run_sh):
    env = dict(re.findall(r'^export (\w+)=(.*)$', run_sh, re.M))
    return {k: [Path(x).name for x in env.get(k, '').strip("'").split(':') if x] for k in ENV_KEYS}, env


def new_side():
    """Board path -> sha of everything the current unified state deploys: the T8 v3 native package (files mapped
    through its mounts), its framework/ overlay, plus window5's runtime/boot fingerprints (what 61b actually had)."""
    seen = {}
    for fpn in ('runtime-fingerprint.txt', 'boot-image-fingerprint.txt'):
        for line in (W5 / fpn).read_text().splitlines():
            h, p = line.split(None, 1)
            seen[p] = h
    pkg = json.loads((V3 / 'native/package.json').read_text())
    mounts = sorted(((m['source'], m['target']) for m in pkg['mounts']), key=lambda x: -len(x[0]))
    for rel, h in pkg['files'].items():
        for src, tgt in mounts:
            if rel == src or rel.startswith(src + '/'):
                seen.setdefault(tgt + rel[len(src):], h)
                break
    for f in (V3 / 'framework').iterdir():
        seen[f'/system/android/framework/{f.name}'] = sha(f.read_bytes())
    fp = {}
    for p, h in seen.items():
        fp.setdefault(Path(p).name, []).append((p, h))
    mapped = {}
    for line in (W5 / 'toutiao/maps-t5-10020.txt').read_text(errors='replace').splitlines():
        p = line.split()[-1] if line.split() else ''
        if p.startswith('/'):
            mapped.setdefault(Path(p).name, set()).add(p)
    return fp, mapped


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'inventory.csv'))
    a = ap.parse_args()
    manifest_ok()
    fp, mapped = new_side()
    old_loads = set()
    import gzip
    for line in gzip.open(OLD_STDERR, 'rt', errors='replace'):
        m = re.match(r'\[SOURCE-NATIVE-LOAD\] path=(\S+)', line)
        if m:
            old_loads.add(Path(m.group(1)).name)
    apk = sweep.apks('toutiao')[0]
    with zipfile.ZipFile(apk) as z:
        apk_libs = {Path(n).name: sha(z.read(n)) for n in z.namelist() if n.startswith('lib/arm64-v8a/')}
    rows = []
    sources = [('tt-rt.tar', RT_BOARD), ('tt-stage.tar', STAGE_BOARD), ('tt-wd.tar', WD_BOARD)]
    envsets = {}
    for tar_name, board in sources:
        with tarfile.open(BUNDLE / tar_name) as t:
            members = [m for m in t.getmembers() if m.isfile()]
            if tar_name == 'tt-rt.tar':
                run_sh = next(t.extractfile(m).read().decode() for m in members if m.name.lstrip('./') == 'run.sh')
                envsets, env = run_env(run_sh)
            for m in members:
                rel = m.name.lstrip('./')
                data = t.extractfile(m).read()
                rows.append(classify(tar_name, board, rel, data, envsets, old_loads, apk_libs, fp, mapped))
    for f in sorted((BUNDLE / 'aot').iterdir()):
        rows.append({'bundle': 'aot', 'old_board_path': f'{RT_BOARD}/oat/arm64/{f.name}',
                     'old_sha256': sha(f.read_bytes())[:16], 'size': f.stat().st_size, 'category': 'app-aot',
                     'old_loader': 'ART app oat (only with --with-aot; 9-27/28 boards ran without)',
                     'new_counterpart': 'none (BMS route runs the app on JIT/interpreter)', 'new_sha256': '',
                     'same': '', 'new_loader': 'n/a'})
    rows.append({'bundle': 'source-host.hap', 'old_board_path': 'bm install org.westlake.imehost',
                 'old_sha256': sha((BUNDLE / 'source-host.hap').read_bytes())[:16],
                 'size': (BUNDLE / 'source-host.hap').stat().st_size, 'category': 'host-hap',
                 'old_loader': 'OH ability that owns the window (WL_PARENT_ID/WL_SUB_WINDOW)',
                 'new_counterpart': 'none: the app is a BMS-installed bundle with its own ability window',
                 'new_sha256': '', 'same': '', 'new_loader': 'n/a'})
    with open(a.out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(len(rows), 'files;', Counter(r['category'] for r in rows).most_common())
    print('same-name status:', Counter((r['category'], r['same']) for r in rows if r['category'] in
                                       ('runtime-native', 'app-lib', 'bcp-jar')).most_common())
    return 0


def classify(tar_name, board, rel, data, envsets, old_loads, apk_libs, fp, mapped):
    name = Path(rel).name
    h = sha(data)
    row = {'bundle': tar_name, 'old_board_path': f'{board}/{rel}', 'old_sha256': h[:16], 'size': len(data)}
    if rel.startswith('lib/arm64-v8a/'):
        a = apk_libs.get(name)
        cat = 'app-lib' if a == h else ('app-lib-PATCHED' if a else 'app-lib-extra')
        if name in envsets['WESTLAKE_ANDROID_NATIVE_TARGETS']:
            ld = 'libart OpenInAndroidNamespace -> westlake_android_app ns (NATIVE_TARGETS, bionic shim preloaded)'
        elif name in envsets['LD_PRELOAD']:
            ld = 'LD_PRELOAD (process-wide, before main)'
        else:
            ld = 'System.loadLibrary via libart source loader (classloader ns, search=asx:/system/lib64:...)'
        if name not in old_loads and name not in envsets['LD_PRELOAD']:
            ld += '; not seen loaded in the 09-25 run'
        new = mapped.get(name)
        row.update(category=cat, old_loader=ld,
                   new_counterpart='/data/app/el1/bundle/public/com.ss.android.article.news/android/lib/arm64-v8a/'
                                   + name + ' (BMS extracts the APK copy)',
                   new_sha256=(a or '')[:16], same=('yes' if a == h else 'no'),
                   new_loader=('mapped at t5 (app classloader ns via libapp_native_loader)' if new else
                               'not mapped at t5 (plain app ns; westlake_native only for 13 whitelisted packages)'))
        return row
    if rel.startswith('fw/'):
        cat, ld = 'bcp-jar', 'boot class path (boot image boot-*.art)'
    elif rel.startswith('boot/'):
        cat, ld = 'boot-image', 'ART boot image (-Ximage), built against fw/*.jar'
    elif rel.startswith('webview-t-lib/'):
        cat = 'webview-native'
        ld = ('LD_PRELOAD + WESTLAKE_ANDROID_NATIVE_PRELOAD (bionic ABI provider)' if name in envsets['LD_PRELOAD']
              else 'WebView provider (ASX_WEBVIEW_LIB_DIR)')
    elif rel.endswith('.so') or '.so.' in rel:
        cat = 'runtime-native'
        ld = []
        if name in envsets['LD_PRELOAD']:
            ld.append('LD_PRELOAD')
        if name in OLD_HOST_OPENS:
            ld.append('appspawn-x dlopen (default ns)')
        if name in old_loads:
            ld.append('System.load/loadLibrary (libart source loader)')
        for k in ('WESTLAKE_PERMISSION_HELPER_PATH', 'WESTLAKE_ACCOUNT_HELPER_PATH', 'WESTLAKE_CONNECTIVITY_HELPER_PATH'):
            if name in envsets[k]:
                ld.append(k)
        ld = ' + '.join(ld) or 'DT_NEEDED / LD_LIBRARY_PATH (default ns, asx first)'
        if rel.endswith('.bak') or 'pre-' in rel:
            cat, ld = 'backup', 'not loaded (backup copy)'
    elif rel in ('appspawn-x',):
        cat, ld = 'host-binary', 'exec by run.sh inside source_app_namespace (mount ns: RT -> /data/local/tmp/asx)'
    elif rel.endswith('.sh') or name in ('host_spawn', 'source_app_namespace', 'screen-gate', 'request.bin'):
        cat, ld = 'launcher/ops', 'run by watchdog / provision'
    elif rel.endswith('.apk'):
        cat, ld = 'apk', ('framework-res' if 'framework-res' in rel else 'WebView provider APK (ASX_WEBVIEW_APK)')
    else:
        cat, ld = 'data/config', 'read by runtime'
    cands = fp.get(name, [])
    if name == 'appspawn-x':
        cands = fp.get('appspawn-x', [])
    row.update(category=cat, old_loader=ld,
               new_counterpart=' | '.join(p for p, _ in cands) or ('mapped: ' + ' | '.join(sorted(mapped[name]))
                                                                     if name in mapped else 'absent'),
               new_sha256=' | '.join(x[:16] for _, x in cands),
               same=('' if not cands else ('yes' if all(x == h for _, x in cands) else 'no')),
               new_loader=('mapped at t5: ' + ' | '.join(sorted(mapped[name]))) if name in mapped else
               ('not mapped at t5' if cands else 'n/a'))
    return row


if __name__ == '__main__':
    sys.exit(main())
