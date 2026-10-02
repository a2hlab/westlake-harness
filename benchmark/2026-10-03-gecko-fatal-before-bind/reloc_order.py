#!/usr/bin/env python3
"""Replay musl's relocation order for a Gecko library in the route-A native domain and report the unresolved strong
symbols in the order musl would hit them (dlopen aborts at the first one).

    reloc_order.py <lib.so> [--extra SYM ...]

Provider model (native domain, westlake_stock_host_main.c CreateConfiguredNamespaces + app_native_loader
flutter_domain.inc): musl itself (NEEDED libc.so / libm.so / libdl.so are musl's reserved names), the RTLD_GLOBAL
westlake_native/libwestlake_native_abi.so (d2053066), the app's own libraries in the same directory, and Android NDK API
symbols from the android lib64 libraries the library NEEDs (A*, __android_log*, gl*, ...). libbionic_compat is NOT in
scope (not inherited for native_private; shared by name only). WEAK undefined symbols never fail. Order: musl reloc_all
= DT_JMPREL, then DT_REL, then DT_RELA. --extra adds symbols to the provider (a candidate export)."""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gecko_imports as gi  # noqa: E402


def tool(n):
    return subprocess.run(['xcrun', '-f', n], capture_output=True, text=True).stdout.strip() or n


def main():
    lib = Path(sys.argv[1])
    extra = set(sys.argv[sys.argv.index('--extra') + 1:]) if '--extra' in sys.argv else set()
    provided = gi.nm(gi.MUSL, False) | gi.nm(gi.PROVIDERS['libwestlake_native_abi.so(d2053066)'], False) | extra
    provided |= set().union(*(gi.nm(l, False) for l in lib.parent.glob('*.so')))
    syms = subprocess.run([tool('llvm-readelf'), '--dyn-syms', str(lib)], capture_output=True, text=True).stdout
    weak = {l.split()[-1].split('@')[0] for l in syms.splitlines() if ' UND ' in l and ' WEAK ' in l}
    rel = subprocess.run([tool('llvm-readelf'), '-r', str(lib)], capture_output=True, text=True).stdout
    sections, cur = {}, None
    for line in rel.splitlines():
        m = re.match(r"Relocation section '([^']+)'", line)
        if m:
            cur = m.group(1)
            sections[cur] = []
            continue
        parts = line.split()
        if cur and len(parts) >= 5 and re.match(r'^[0-9a-f]{8,}$', parts[0]):
            sections[cur].append(parts[4].split('@')[0])
    order = [s for s in sections if 'plt' in s] + [s for s in sections if 'plt' not in s]
    seen, missing = set(), []
    for sec in order:
        for s in sections[sec]:
            if s in seen or s in provided or s in weak or gi.NDK.match(s) or s in ('0', ''):
                continue
            seen.add(s)
            missing.append((sec, s))
    print(f'{lib.name}: unresolved strong symbols in musl order ({len(missing)}):',
          ', '.join(f'{s} [{sec}]' for sec, s in missing) or 'none')


if __name__ == '__main__':
    main()
