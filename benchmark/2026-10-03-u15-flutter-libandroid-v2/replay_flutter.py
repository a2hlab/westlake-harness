#!/usr/bin/env python3
"""musl-order replay of immich's arm64 libraries in the route-A FLUTTER-PRIVATE domain, with a chosen
westlake_flutter/ directory searched first (the Flutter domain's search prefix).

    replay_flutter.py <apk-libs-dir> <westlake_flutter-dir> [--global <lib.so> ...]

Thin wrapper over ../2026-10-03-u15-compat-v3/replay_normal.py (same musl scope model: is_global DSOs + the library's
own NEEDED closure + itself; JMPREL, REL, RELA; WEAK never fails; versions per check_verinfo): only its NEEDED resolution
is replaced so that <westlake_flutter-dir> is searched right after the app's own directory, as flutter_domain.inc does.
Globals for the Flutter domain: the westlake_flutter libwestlake_native_abi.so (host RTLD_GLOBAL) and the resident
runtime (published RTLD_GLOBAL by needs_runtime, which includes every flutter_private app). The parent's NDK-name
shortcut (A*_ names counted as provided) is switched off: the domain's libandroid is the object under test."""
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('rn', HERE.parent / '2026-10-03-u15-compat-v3/replay_normal.py')
rn = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rn)

libs, fdir = Path(sys.argv[1]), Path(sys.argv[2])


def resolve(name, app, bundle):
    for d in [app, fdir, bundle, rn.POOL, rn.POOL / 'platformsdk', rn.POOL / 'chipset-sdk-sp', rn.POOL / 'ndk']:
        if (d / name).is_file():
            return d / name
    return None


rn.resolve = resolve
# The library under test IS the domain's libandroid: NDK names must be found in a real provider, not assumed.
rn.gi.NDK = re.compile(r"(?!x)x")
sys.argv = ['replay_normal.py', str(libs)] + sys.argv[3:]
rn.main()
