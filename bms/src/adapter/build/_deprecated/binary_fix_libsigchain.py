#!/usr/bin/env python3
# === GUARD: internal helper, do not invoke directly ===
import os as _bi_os, sys as _bi_sys
if _bi_os.environ.get("BUILD_INNER_INVOKED") != "1":
    print("[GUARD] " + _bi_os.path.basename(_bi_sys.argv[0]) + " is an internal helper — invoke via build_*.sh / restore_after_sync.sh / etc.", file=_bi_sys.stderr)
    print("[GUARD] Escape hatch (debug only): BUILD_INNER_INVOKED=1 python3 " + _bi_os.path.basename(_bi_sys.argv[0]), file=_bi_sys.stderr)
    _bi_sys.exit(2)
# === END GUARD ===
"""
patch_libsigchain.py — apply binary patch to libsigchain.so.

Problem:
  libsigchain.so is compiled with ANDROID_HOST_MUSL which embeds the string
  "libc_musl.so" and later dlopen()s it at runtime. On OH the actual libc is
  ld-musl-arm.so.1 (usually reachable as "libc.so"), so dlopen fails and
  abort()s inside sigchain's static initializer — killing appspawn-x before
  main() even runs.

Fix:
  Replace the 12-byte string "libc_musl.so" with "libc.so\\0\\0\\0\\0\\0"
  (same 12 bytes, NUL-terminated early) directly in the ELF. This is a true
  fix at the binary level; runtime behavior becomes dlopen("libc.so") which
  resolves correctly on OH.

Usage:
  python3 patch_libsigchain.py <input_so> [output_so]

  If output_so is omitted, patches in place (writing backup to <input>.orig).

History:
  - 2026-04-08: first manual hex edit done for device deploy
  - 2026-04-14: formalized as script (previously an unrecorded manual step,
    violating the restore_after_sync.sh invariant)
"""

import os
import shutil
import sys


NEEDLE = b"libc_musl.so\x00"  # 13 bytes: 12 chars + terminating NUL
REPLACE = b"libc.so\x00\x00\x00\x00\x00\x00"  # 13 bytes: 7 chars + 6 NULs


def patch(path_in: str, path_out: str) -> int:
    with open(path_in, "rb") as fh:
        data = fh.read()

    count = data.count(NEEDLE)
    if count == 0:
        # Check if already patched
        if b"libc.so\x00\x00\x00\x00\x00\x00" in data and b"libc_musl" not in data:
            print(f"  [skip] {path_in} already patched")
            if path_in != path_out:
                shutil.copy2(path_in, path_out)
            return 0
        print(f"  [warn] needle 'libc_musl.so' not found in {path_in}")
        return 1

    patched = data.replace(NEEDLE, REPLACE)

    # Sanity: length preserved
    if len(patched) != len(data):
        print(f"  [fail] length mismatch: {len(data)} -> {len(patched)}")
        return 2

    # Sanity: no residual
    if b"libc_musl" in patched:
        print(f"  [fail] residual 'libc_musl' substring after patch")
        return 3

    with open(path_out, "wb") as fh:
        fh.write(patched)

    print(f"  [ok]   patched {count} occurrence(s) of 'libc_musl.so' -> 'libc.so\\0...' in {path_out}")
    return 0


def main(argv):
    if len(argv) < 2 or len(argv) > 3:
        print(__doc__)
        return 2

    path_in = argv[1]
    path_out = argv[2] if len(argv) == 3 else path_in

    if not os.path.isfile(path_in):
        print(f"  [fail] input file not found: {path_in}")
        return 2

    if path_in == path_out:
        backup = path_in + ".orig"
        if not os.path.exists(backup):
            shutil.copy2(path_in, backup)
            print(f"  [bak]  saved original to {backup}")

    return patch(path_in, path_out)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
