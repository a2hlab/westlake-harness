#!/usr/bin/env python3
"""#46 fallback: prepend the app's bundled BoringSSL (libttcrypto.so) to the existing
LD_PRELOAD so default-namespace HMAC/EVP resolution is self-consistent, regardless of
how a default-namespace consumer of the tt pair was loaded (System.loadLibrary or a
native dlopen the target list cannot reach).

libttcrypto self-contains HMAC_Init_ex + HMAC_CTX_init + EVP_* (DT_NEEDED only libc/m/dl),
so one entry, placed first, makes every unversioned HMAC reference in the default namespace
bind to BoringSSL. Placed before the existing shims (which do not use crypto).
usage: apply_ld_preload.py <run.sh in> <run.sh out>
"""
import re
import sys

LIB = '/data/local/tmp/asx/lib/arm64-v8a/libttcrypto.so'
src, dst = sys.argv[1], sys.argv[2]
text = open(src).read()
pat = re.compile(r'^(export LD_PRELOAD=)(\S*)$', re.M)
m = pat.search(text)
if m is None or len(pat.findall(text)) != 1:
    sys.exit('expected exactly one LD_PRELOAD export')
entries = [e for e in m.group(2).split(':') if e]
if LIB in entries:
    print('already present')
else:
    entries.insert(0, LIB)
text = text[:m.start(2)] + ':'.join(entries) + text[m.end(2):]
open(dst, 'w').write(text)
print('LD_PRELOAD =', ':'.join(entries))
