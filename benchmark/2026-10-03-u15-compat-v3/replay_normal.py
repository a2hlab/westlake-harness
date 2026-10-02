#!/usr/bin/env python3
"""musl-order relocation replay of an app's arm64 libraries in the route-A NORMAL app domain, listing EVERY unresolved
strong symbol per library (not only the first musl would stop at).

    replay_normal.py <apk-libs-dir> [--global <lib.so> ...] [--bundle <payload/android/lib64>] [--native-domain] [--json out]

Lookup scope (OH musl dynlink.c add_can_search_so_list_in_dso / find_sym_by_saved_so_list): every is_global DSO in the
process, plus the dlopen root's dependency tree. So a library sees: musl (libc/libm/libdl are musl's reserved names),
itself, the --global set, and its NEEDED closure as the normal domain resolves it: the app's own libraries first, then the
android lib64 libraries of the deployed bundle (liblog, libandroid, ... shared by name into the app namespace), then
the platform pool. Version check (check_verinfo): a provider without .gnu.version_d accepts any versioned import, so
version never blocks these providers. WEAK undefined never fails; NDK API names (gecko_imports.NDK) are counted as
provided by the NDK libraries. Order: DT_JMPREL, then DT_REL, then DT_RELA (reloc_all)."""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
sys.path.insert(0, str(REPO / 'benchmark/2026-10-03-gecko-fatal-before-bind'))
import gecko_imports as gi  # noqa: E402
import lab_paths  # noqa: E402

WS = lab_paths.workspaces()
BUNDLE = WS / 'westlake-inputs/generations/u13-stageA-91272eaf-20261003/armed-bundle/native/payload/android/lib64'
POOL = WS / 'westlake-harness-bms-deploy/bms/src/.work/b68-generation/platform-pool/system/lib64'
MUSL_NAMES = {'libc.so', 'libm.so', 'libdl.so', 'ld-musl-aarch64.so.1'}


def rd(*a):
    return subprocess.run(['llvm-readelf', *map(str, a)], capture_output=True, text=True).stdout


def needed(lib):
    return re.findall(r'\(NEEDED\)\s+Shared library: \[(.+?)\]', rd('-d', lib))


NATIVE = False  # --native-domain: westlake_native/ is searched first (flutter_domain.inc native_selected)


def resolve(name, app, bundle):
    dirs = [app] + ([bundle / 'westlake_native'] if NATIVE else []) + [bundle, POOL, POOL / 'platformsdk',
                                                                       POOL / 'chipset-sdk-sp', POOL / 'ndk']
    for d in dirs:
        if (d / name).is_file():
            return d / name
    return None


def closure(lib, app, bundle):
    seen, out, todo, missing = set(), [], [lib], []
    while todo:
        cur = todo.pop(0)
        for n in needed(cur):
            if n in MUSL_NAMES or n in seen:
                continue
            seen.add(n)
            p = resolve(n, app, bundle)
            if p is None:
                missing.append(n)
                continue
            out.append(p)
            todo.append(p)
    return out, missing


def relocs(lib):
    sections, cur = {}, None
    for line in rd('-r', '-W', lib).splitlines():
        m = re.match(r"Relocation section '([^']+)'", line)
        if m:
            cur = m.group(1)
            sections[cur] = []
            continue
        p = line.split()
        if cur and len(p) >= 5 and re.match(r'^[0-9a-f]{8,}$', p[0]):
            sections[cur].append(p[4].split('@')[0])
    return [s for s in sections if 'plt' in s] + [s for s in sections if 'plt' not in s], sections


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('libs', type=Path)
    ap.add_argument('--global', dest='glob', nargs='*', default=[], type=Path)
    ap.add_argument('--bundle', type=Path, default=BUNDLE)
    ap.add_argument('--json', type=Path)
    ap.add_argument('--native-domain', action='store_true')
    a = ap.parse_args()
    global NATIVE
    NATIVE = a.native_domain
    musl = gi.nm(gi.MUSL, False)
    glob = set().union(*(gi.nm(g, False) for g in a.glob)) if a.glob else set()
    report = {}
    for lib in sorted(a.libs.glob('*.so')):
        deps, unres = closure(lib, a.libs, a.bundle)
        provided = musl | glob | gi.nm(lib, False) | (set().union(*(gi.nm(d, False) for d in deps)) if deps else set())
        syms = rd('--dyn-syms', '-W', lib)
        weak = {l.split()[7].split('@')[0] for l in syms.splitlines() if ' UND ' in l and ' WEAK ' in l and len(l.split()) >= 8}
        ver = {l.split()[7].split('@')[0]: l.split()[7].split('@', 1)[1] for l in syms.splitlines()
               if ' UND ' in l and len(l.split()) >= 8 and '@' in l.split()[7]}
        order, sections = relocs(lib)
        seen, missing = set(), []
        for sec in order:
            for s in sections[sec]:
                if s in seen or s in provided or s in weak or gi.NDK.match(s) or s in ('0', ''):
                    continue
                seen.add(s)
                missing.append({'symbol': s, 'section': sec, 'version': ver.get(s, '')})
        report[lib.name] = {'needed_closure': [str(d).replace(str(WS), '$WORKSPACES') for d in deps],
                            'needed_unresolved': unres, 'missing': missing}
        print(f"{lib.name}: {len(missing)} missing" + (': ' + ', '.join(f"{m['symbol']}@{m['version'] or '-'} [{m['section']}]" for m in missing) if missing else '')
              + (f'   (NEEDED not found: {unres})' if unres else ''))
    if a.json:
        a.json.write_text(json.dumps(report, indent=1) + '\n')


if __name__ == '__main__':
    main()
