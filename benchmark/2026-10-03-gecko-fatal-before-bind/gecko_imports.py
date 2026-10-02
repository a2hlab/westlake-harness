#!/usr/bin/env python3
"""Static: which libc-class symbols do the Gecko native libraries import that OH musl does not define, and who on
route A exports them.   gecko_imports.py <apk-libs-dir> [<label>]  -> prints a table; --json for machine output

For each lib/arm64-v8a/*.so: undefined dynamic symbols, minus symbols defined by the app's own libraries, minus symbols
defined by the board's musl (ld-musl-aarch64.so.1 from $WORKSPACES/westlake-inputs/oh61-link-inputs/system-lib64).
What is left is split into Android NDK API symbols (A*, __android_log*, gl*, egl*, AndroidBitmap_*: provided by the
android lib64 libraries the libs NEED) and libc-class symbols. Each libc-class symbol is checked against the deployed
U12 route-A ABI providers (hashes from the U12 runtime-fingerprint.txt): libbionic_compat.so 015aa3a6,
libwestlake_native_abi.so d2053066, android lib64 libc.so stub ee6034f5."""
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'scripts/lab'))
import lab_paths  # noqa: E402

WS = lab_paths.workspaces()
PROVIDERS = {
    'libbionic_compat.so(015aa3a6)': WS / 'westlake-inputs/generations/n11h-u101t8-host65ac5089-v1/native/payload/route/libbionic_compat.so',
    'libwestlake_native_abi.so(d2053066)': WS / 'westlake-generation-n10-63b6f8d4/payload/android/lib64/libwestlake_native_abi.so',
    'android-libc.so-stub(ee6034f5)': WS / 'westlake-generation-n2-candidate/payload/android/lib64/libc.so',
}
MUSL = WS / 'westlake-inputs/oh61-link-inputs/system-lib64/ld-musl-aarch64.so.1'
NDK = re.compile(r'^(A[A-Z][A-Za-z]+_|__android_log|gl[A-Z]|egl[A-Z]|AndroidBitmap_|ANativeWindow|AHardwareBuffer|ASurface|AChoreographer|AMedia|AImage|AAsset|AConfiguration|ALooper|AInputQueue|ASensor)')


def nm(path, undefined):
    tool = subprocess.run(['xcrun', '-f', 'llvm-nm'], capture_output=True, text=True).stdout.strip() or 'llvm-nm'
    args = [tool, '-D', '--undefined-only' if undefined else '--defined-only', str(path)]
    out = subprocess.run(args, capture_output=True, text=True).stdout
    return {l.split()[-1].split('@')[0] for l in out.splitlines() if l.strip()}


def main():
    d = Path(sys.argv[1])
    libs = sorted(d.glob('*.so'))
    own = set().union(*(nm(l, False) for l in libs))
    musl = nm(MUSL, False)
    prov = {k: nm(v, False) for k, v in PROVIDERS.items()}
    rows = {}
    for l in libs:
        miss = sorted(nm(l, True) - own - musl)
        libc = [s for s in miss if not NDK.match(s)]
        rows[l.name] = {'ndk_api': len(miss) - len(libc),
                        'libc_class': {s: [k for k, v in prov.items() if s in v] for s in libc}}
    if '--json' in sys.argv:
        print(json.dumps(rows, indent=1))
        return
    for name, r in rows.items():
        if not r['libc_class']:
            continue
        print(f"{name}: {len(r['libc_class'])} libc-class symbol(s) musl lacks ({r['ndk_api']} NDK API symbols not listed)")
        for s, who in r['libc_class'].items():
            print(f"    {s:32s} {'exported by ' + ', '.join(who) if who else 'NOT exported by any route-A ABI provider'}")


if __name__ == '__main__':
    main()
