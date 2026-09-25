#!/usr/bin/env python3
"""#46: which APK libraries must load in the Android-ABI namespace so that no
default-namespace copy of libttboringssl.so / libttcrypto.so is ever created.

A library loaded in the default namespace whose DT_NEEDED closure reaches the
tt crypto pair loads a second copy of the pair there, and OH musl binds that
copy's BoringSSL imports in load order across the default namespace, where OH's
libcrypto_openssl.z.so (OpenSSL 3) precedes it.
usage: tt_closure.py <apk-lib-dir> <current-targets(colon list)>
"""
import subprocess
import sys
from pathlib import Path

lib_dir = Path(sys.argv[1])
current = set(filter(None, sys.argv[2].split(':')))
seeds = {'libttboringssl.so', 'libttcrypto.so'}


def needed(p):
    out = subprocess.run(['readelf', '-d', str(p)], capture_output=True, text=True).stdout
    return {l.split('[', 1)[1].split(']', 1)[0] for l in out.splitlines() if '(NEEDED)' in l}


def defined(p):
    out = subprocess.run(['readelf', '-W', '--dyn-syms', str(p)], capture_output=True, text=True).stdout
    names = set()
    for l in out.splitlines():
        f = l.split()
        if len(f) >= 8 and f[6] != 'UND' and f[3] in ('FUNC', 'OBJECT'):
            names.add(f[7].split('@')[0])
    return names


libs = {p.name: needed(p) for p in lib_dir.glob('*.so')}
closure = set(seeds)
while True:
    grown = {n for n, deps in libs.items() if deps & closure} - closure
    if not grown:
        break
    closure |= grown

print('reverse-dependency closure of the tt crypto pair (%d):' % len(closure))
for n in sorted(closure):
    print('  %-28s %s' % (n, 'already target' if n in current else 'ADD'))
missing = {d for n in closure for d in libs.get(n, ())
           if d not in libs and not d.startswith(('libc.so', 'libdl.so', 'libm.so', 'libz.so', 'liblog.so'))}
print('non-APK deps of the closure (resolved by the namespace search path):', sorted(missing))

pair = defined(lib_dir / 'libttcrypto.so') | defined(lib_dir / 'libttboringssl.so')
for other in sorted(libs):
    if other in seeds:
        continue
    clash = defined(lib_dir / other) & pair & {s for s in pair if s.startswith(('HMAC', 'EVP_', 'SSL_', 'CRYPTO_', 'SHA'))}
    if len(clash) > 20:
        print('also exports %d BoringSSL-family names: %s (in closure: %s)' % (len(clash), other, other in closure))

print()
print('WESTLAKE_ANDROID_NATIVE_TARGETS=' + ':'.join(sorted(current | closure, key=lambda s: (s not in current, s))))
