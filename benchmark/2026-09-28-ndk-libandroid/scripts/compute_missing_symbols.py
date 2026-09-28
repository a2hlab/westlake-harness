#!/usr/bin/env python3
"""T4 offline: compute the libandroid NDK symbol gap for fd-stk (SuperTuxKart).

Method (spec: specs/app-lighting/t4-ndk-libandroid.spec.md, "缺口口径"):
- Take fd-stk's staged DSOs (libSDL2.so, libmain.so) from the APK.
- Collect STRONG (bind != WEAK) GLOBAL UND symbols in the A* NDK cluster.
- Model the ACTUAL resolution scope in the app namespace, in load order:
  * the runtime-root libandroid.so that libSDL2's DT_NEEDED actually binds to
    (sha256 must equal the framework report's; provenance: native-runtime build),
  * every DSO visible in the global scope BEFORE libSDL2 loads (its transitive
    closure providers, per the loader trace), including libhwui.so (which
    provides ANativeWindow_* as a transitive DT_NEEDED of libandroid.so),
  * the LD_PRELOAD'ed bionic shim (provides ANativeWindow_lock/unlockAndPost),
  * NOT the webview-t-lib libandroid.so copy: same soname, later in the search
    order, never enters scope (the runtime error names AConfiguration_new, not
    AAsset_* — only the runtime-root build has the AAsset set).
- No symbol-version suffixes exist on any A* UND reference (readelf-verified),
  so version comparison reduces to name comparison for this cluster.
- Cross-check: the reported error symbol must be in the missing set.

Usage: compute_missing_symbols.py --out results.json [--write]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

APK = Path('/Users/zhaoyue/orca/workspaces/westlake-inputs/apks/fdroid100/org.supertuxkart.stk_311.apk')
# Board framework-2 report (5ea34a45) pins the libandroid.so that is actually
# resolved; the same file is mirrored in the VM native-runtime build dir.
RUNTIME_LIBANDROID = Path('/home/zhaoyue/a2hlab/ws/out.75d82d5/native-runtime/libandroid.so')
GLOBAL_SCOPE_LIBS = [
    # name, path — everything in the app-namespace global scope before libSDL2
    Path('/home/zhaoyue/a2hlab/ws/out.75d82d5/native-runtime/libhwui.so'),
    Path('/home/zhaoyue/a2hlab/ws/out/native-runtime/libwl_missing_natives.so'),
    Path('/home/zhaoyue/a2hlab/ws/out/native-runtime/libwl_opengl_jni.so'),
    Path('/home/zhaoyue/a2hlab/ws/out.75d82d5/webview-input-source/webview-t-lib/libwebview_bionic_shim.so'),
]
FRAMEWORK_REPORT = Path('/home/zhaoyue/a2hlab/board/5ea34a4500000000000000001123012c/framework-2/device-report.json')
ORIGINAL_ERROR_SYMBOL = 'AConfiguration_new'  # stk_stubnl.child.stderr:351 (merged48 evidence)

NDK_A_PREFIXES = ('AAsset', 'AAssetManager', 'AConfiguration', 'ALooper',
                  'ANativeWindow', 'ASensor', 'ASensorEventQueue', 'ASensorManager')


def readelf_dynsyms(path):
    out = subprocess.run(['readelf', '--dyn-syms', '-W', str(path)],
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise RuntimeError(f'readelf failed on {path}: {out.stderr.strip()}')
    rows = []
    for line in out.stdout.splitlines():
        f = line.split()
        if len(f) < 8 or not f[0].rstrip(':').isdigit():
            continue
        rows.append({'num': f[0].rstrip(':'), 'value': f[1], 'size': f[2],
                     'type': f[3], 'bind': f[4], 'vis': f[5], 'ndx': f[6],
                     'name': f[7]})
    return rows


def defined_names(path):
    return {(r['name'].split('@')[0]) for r in readelf_dynsyms(path) if r['ndx'] != 'UND'}


def und_strong(path, prefixes):
    names = []
    for r in readelf_dynsyms(path):
        if r['ndx'] != 'UND' or r['bind'] == 'WEAK':
            continue
        base = r['name'].split('@')[0]
        if base.startswith(prefixes) and '@' in r['name']:
            raise ValueError(f'versioned NDK A* reference, model does not cover: {r["name"]} in {path}')
        if base.startswith(prefixes):
            names.append(base)
    return sorted(set(names))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--write', action='store_true', help='write the repo results.json')
    args = ap.parse_args()

    # 1) framework-report hash pin: the model must run against the exact build
    #    the board actually resolves.
    report = json.loads(FRAMEWORK_REPORT.read_text())
    want = report['files']['libandroid.so']
    import hashlib
    got_sha = hashlib.sha256(RUNTIME_LIBANDROID.read_bytes()).hexdigest()
    if got_sha != want['sha256']:
        raise SystemExit(f'libandroid.so mismatch: local {got_sha[:12]}… != report {want["sha256"][:12]}…')

    # 2) required set from the app DSOs
    need = []
    for dso in ('lib/arm64-v8a/libSDL2.so', 'lib/arm64-v8a/libmain.so'):
        p = Path('/tmp') / ('t4_dso_' + dso.replace('/', '_'))
        if not p.is_file():
            subprocess.run(['unzip', '-p', str(APK), dso], stdout=p.open('wb'), check=True)
        n = und_strong(p, NDK_A_PREFIXES)
        need.append({'dso': dso, 'symbols': n})

    # 3) actual resolution scope
    scope = [{'name': 'libandroid.so (runtime root, framework-pinned)',
              'path': str(RUNTIME_LIBANDROID),
              'provides': sorted(defined_names(RUNTIME_LIBANDROID))}]
    for lib in GLOBAL_SCOPE_LIBS:
        scope.append({'name': lib.name, 'path': str(lib),
                      'provides': sorted(defined_names(lib))})

    # 4) resolve
    missing, providers = [], {}
    all_syms = sorted({s for entry in need for s in entry['symbols']})
    for sym in all_syms:
        provs = [s['name'] for s in scope if sym in s['provides']]
        if provs:
            providers[sym] = provs
        else:
            missing.append(sym)

    # 5) cross-check against the original runtime error
    error_ok = ORIGINAL_ERROR_SYMBOL in missing

    result = {
        'task': 't4-ndk-libandroid offline gap computation',
        'date': '2026-09-28',
        'board': '5ea34a4500000000000000001123012c',
        'framework_report': str(FRAMEWORK_REPORT),
        'resolved_libandroid': {
            'path': str(RUNTIME_LIBANDROID), 'sha256': got_sha,
            'bytes': want['bytes'],
            'origin': 'out.75d82d5/native-runtime (link_native_platform.py assembly)'},
        'required': need,
        'scope': [{'name': s['name'], 'path': s['path']} for s in scope],
        'providers': providers,
        'missing_symbols': missing,
        'missing_count': len(missing),
        'original_error_symbol': ORIGINAL_ERROR_SYMBOL,
        'original_error_in_missing': error_ok,
        'display': {'resolution': '1200x1920', 'refresh_hz': 60,
                    'physical_mm': [107, 172], 'dpi_hint': 284},
    }
    if not error_ok:
        result['ERROR'] = (f'{ORIGINAL_ERROR_SYMBOL} not in missing set — model diverges '
                           'from the original runtime error; refusing to emit')
        json.dump(result, args.out.open('w'), indent=1)
        raise SystemExit(1)

    json.dump(result, args.out.open('w'), indent=1)
    print(f'missing_count={len(missing)} error_in_missing={error_ok}')
    for s in missing:
        print(' ', s)
    if args.write:
        repo = Path(__file__).resolve().parents[1] / 'results.json'
        repo.write_text(json.dumps(result, indent=1) + '\n')
        print('wrote', repo)


if __name__ == '__main__':
    main()
