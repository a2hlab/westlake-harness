"""Derive per-app Android-ABI and network-translation native targets from APK DSOs.

An APK .so whose undefined symbols hit bionic-only surface (exported by
libwebview_bionic_shim.so but not by OH musl) silently fails to load unless it is
listed as --android-native-target; ones importing the bionic getaddrinfo family
additionally need --android-native-net-target. Hand-maintaining that list per app
does not scale -- toutiao's list missed libsscronet.so and the feed came up empty
(outer-loop #17 notes). This module derives both lists offline from the APK's
lib/arm64-v8a/*.so using nm, plus the dependency closure rule: a DSO that is
DT_NEEDED by a native target is itself a native target.

CLI: --app-inputs ROOT --shim PATH [--out DIR]   (offline; no board involved)
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

# Wildcards cover the families the shim exports under one prefix.
_BIONIC_ONLY_PREFIXES = ("android_fdsan_", "__android_log_", "__system_property_")
_BIONIC_ONLY_EXACT = {
    # shim-exported single symbols plus the entry's mandated core set
    "__sF", "__errno", "__register_atfork", "android_set_abort_message",
    "__gnu_strerror_r", "__get_h_errno", "android_fdsan_exchange_owner_tag",
}
_NET_FAMILY = {"getaddrinfo", "freeaddrinfo", "gethostbyname", "gethostbyaddr", "getnameinfo"}


def _nm(path: Path, args: list[str]) -> list[str]:
    proc = subprocess.run(["nm", "-D", *args, str(path)], capture_output=True, text=True)
    if proc.returncode != 0:
        return []
    names = []
    for line in proc.stdout.splitlines():
        parts = line.split()
        if parts:
            names.append(re.sub(r"@+.*$", "", parts[-1]))
    return names


def shim_exports(shim: Path) -> set[str]:
    """Symbols the bionic shim provides (source: libwebview_bionic_shim.so .dynsym)."""
    return set(_nm(shim, ["--defined-only"]))


def is_bionic_only(symbol: str, shim: set[str]) -> bool:
    if symbol in _NET_FAMILY:
        return False
    if symbol in _BIONIC_ONLY_EXACT or symbol in shim:
        return True
    return any(symbol.startswith(p) for p in _BIONIC_ONLY_PREFIXES)


def dt_needed(so: Path) -> list[str]:
    """Direct DT_NEEDED entries (basename) of an ELF."""
    out = subprocess.run(["readelf", "-d", str(so)], capture_output=True, text=True)
    if out.returncode != 0:
        return []
    needed = []
    for line in out.stdout.splitlines():
        m = re.search(r"(?:Shared library|NEEDED):\s*\[(.*)\]", line)
        if m and m.group(1):
            needed.append(Path(m.group(1)).name)
    return needed


def derive_app(app_dir: Path, shim: set[str]) -> dict:
    """{'native': [(so, [sample hits])], 'net': [so]} for one app's prepared input dir."""
    libdirs = [app_dir / "lib" / "arm64-v8a"]
    libs = sorted({p for d in libdirs for p in d.glob("*.so")})
    by_name = {p.name: p for p in libs}
    native: dict[str, list[str]] = {}
    net: set[str] = set()
    for so in libs:
        undefined = _nm(so, ["--undefined-only"])
        hits = [s for s in undefined if is_bionic_only(s, shim)]
        if hits:
            native[so.name] = hits
            if any(s in _NET_FAMILY for s in undefined):
                net.add(so.name)
    # dependency closure: DT_NEEDED of a native target is a native target too
    changed = True
    while changed:
        changed = False
        for name in list(native):
            for dep in dt_needed(by_name[name]):
                if dep in by_name and dep not in native:
                    native[dep] = ["(dependency closure)"]
                    changed = True
    return {"native": sorted(native), "native_samples": {k: native[k][:3] for k in native},
            "net": sorted(net)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--app-inputs", required=True, type=Path)
    parser.add_argument("--shim", required=True, type=Path)
    parser.add_argument("--out", type=Path, help="write NATIVE-TARGETS JSON here")
    args = parser.parse_args(argv)

    shim = shim_exports(args.shim)
    derived: dict[str, dict] = {}
    for app_dir in sorted(p for p in args.app_inputs.iterdir() if p.is_dir()):
        derived[app_dir.name] = derive_app(app_dir, shim)
    payload = {"shim": str(args.shim), "shim_symbol_count": len(shim), "apps": derived}
    text = json.dumps(payload, indent=1, sort_keys=True) + "\n"
    if args.out:
        args.out.write_text(text)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
