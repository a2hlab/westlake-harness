#!/usr/bin/env python3
"""musl-order relocation replay of the two Realm consumers against a real native_abi build, with the libz each app
actually gets (Element: the private zlib westlake_native/libz.so 50b9ab6a, LOCAL_NS_PREFERED; McDonald's: the platform
libz the bridge inherit shares from the default namespace, platform-pool platformsdk/libz.so 3c025525), plus the version
check that every @LIBC import sent to native_abi is defined there at version LIBC.

    replay_v2.py <libwestlake_native_abi.so>

Provider model and order: ../2026-10-03-gecko-fatal-before-bind/reloc_order.py (musl + RTLD_GLOBAL native_abi + the app's
own libraries + NDK API symbols for liblog/libandroid; JMPREL, then REL, then RELA; WEAK never fails), with the libz
exports passed as --extra (libz is a NEEDED of both libraries and resolves before relocation), and the FULL exports of the
two other non-musl NEEDED libraries as the native domain resolves them (musl searches a library's dependencies):
liblog.so -> android/lib64/liblog.so 8c81a937 (exports __open_2, __strncpy_chk2, strtoll_l, strtoull_l @@LIBC) and
libandroid.so -> android/lib64/westlake_native/libandroid.so ee2fb82c (exports __cmsg_nxthdr @@LIBC). Without them the
replay does not reproduce the boards' U12 first fatal; with them it does (control run with the deployed d2053066)."""
import io
import contextlib
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
sys.path.insert(0, str(REPO / 'benchmark/2026-10-03-gecko-fatal-before-bind'))
sys.path.insert(0, str(REPO / 'benchmark/2026-10-03-u14-native-abi-gecko'))
import lab_paths  # noqa: E402
import gecko_imports as gi  # noqa: E402
import reloc_order as ro  # noqa: E402
import replay_with_abi as rwa  # noqa: E402

WS = lab_paths.workspaces()
SCAN = WS / 'westlake-harness-bms/benchmark/2026-10-01-u11-native/.artifacts'
CASES = [
    ('mcdonalds', SCAN / 'window-r3-scan/consumers/mcdonalds/mcdonalds.config.arm64_v8a.apk/librealmc.so',
     WS / 'westlake-harness-bms-deploy/bms/src/.work/b68-generation/platform-pool/system/lib64/platformsdk/libz.so',
     'bridge-inherited platform libz'),
    ('fd-im-vector-app', SCAN / 'window-r2-scan/consumers/fd-im-vector-app/fd-im-vector-app.apk/librealm-jni.so',
     WS / 'westlake-inputs/generations/u13-stageA-91272eaf-20261003/armed-bundle/native/payload/android/lib64/westlake_native/libz.so',
     'private zlib (U11ZlibRoot, LOCAL_NS_PREFERED)'),
]
LIB64 = WS / 'westlake-inputs/generations/u13-stageA-91272eaf-20261003/armed-bundle/native/payload/android/lib64'
NEEDED = {'liblog.so': LIB64 / 'liblog.so', 'libandroid.so': LIB64 / 'westlake_native/libandroid.so'}


def sha(p):
    return subprocess.run(['shasum', '-a', '256', str(p)], capture_output=True, text=True).stdout.split()[0]


def main():
    abi = Path(sys.argv[1])
    gi.PROVIDERS['libwestlake_native_abi.so(d2053066)'] = abi
    defs = rwa.versioned_defs(abi)
    print(f'native_abi {abi.name} sha256 {sha(abi)}; LIBC hash {rwa.elf_hash("LIBC"):#x}')
    for key, lib, libz, how in CASES:
        print(f'## {key}: {lib.name} {sha(lib)[:16]}; libz = {how} {sha(libz)[:16]}')
        zsyms = set(gi.nm(libz, False))
        dyn = subprocess.run([ro.tool('llvm-readelf'), '-d', str(lib)], capture_output=True, text=True).stdout
        for name, path in NEEDED.items():
            if f'[{name}]' in dyn:
                zsyms |= gi.nm(path, False)
                print(f'   NEEDED {name} -> {path.relative_to(WS)} {sha(path)[:16]}')
        sys.argv = ['reloc_order.py', str(lib), '--extra', *sorted(zsyms)]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            ro.main()
        print(buf.getvalue().strip())
        und = subprocess.run([ro.tool('llvm-readelf'), '--dyn-syms', '-W', str(lib)], capture_output=True, text=True).stdout
        wanted = {p[7].split('@')[0] for p in (l.split() for l in und.splitlines())
                  if len(p) >= 8 and p[6] == 'UND' and p[7].endswith('@LIBC')}
        sent = sorted(s for s in wanted if s in defs)
        bad = [s for s in sent if defs[s] != 'LIBC']
        print(f'   @LIBC imports defined by native_abi: {len(sent)} ({", ".join(sent)}); version mismatches: {bad or "none"}')


if __name__ == '__main__':
    main()
