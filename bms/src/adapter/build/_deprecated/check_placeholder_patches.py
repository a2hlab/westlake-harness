#!/usr/bin/env python3
# === GUARD: internal helper, do not invoke directly ===
import os as _bi_os, sys as _bi_sys
if _bi_os.environ.get("BUILD_INNER_INVOKED") != "1":
    print("[GUARD] " + _bi_os.path.basename(_bi_sys.argv[0]) + " is an internal helper — invoke via build_*.sh / restore_after_sync.sh / etc.", file=_bi_sys.stderr)
    print("[GUARD] Escape hatch (debug only): BUILD_INNER_INVOKED=1 python3 " + _bi_os.path.basename(_bi_sys.argv[0]), file=_bi_sys.stderr)
    _bi_sys.exit(2)
# === END GUARD ===
"""
check_placeholder_patches.py — detect placeholder patches that cannot be applied.

A placeholder patch is one whose `@@` hunk header contains literal `xxx` instead
of real line numbers (e.g. `@@ -xxx,6 +xxx,28 @@`). The `patch -p1` command will
refuse such files, and `restore_after_sync.sh` silently skips them — meaning the
intended source modifications were never made on ECS.

Run from anywhere:
    python3 build/check_placeholder_patches.py [--root D:/code/adapter]

Exit codes:
    0  no placeholder patches found
    1  one or more placeholder patches detected (printed to stderr)

This is gap 0.2 instrumentation. The 4 known placeholders as of 2026-04-11 are:
    - ohos_patches/ability_rt/services/appmgr/src/app_mgr_service_inner.cpp.patch
    - ohos_patches/bundle_framework/interfaces/inner_api/appexecfwk_base/include/bundle_constants.h.patch
    - ohos_patches/bundle_framework/services/bundlemgr/include/installd/installd_interface.h.patch
    - ohos_patches/bundle_framework/services/bundlemgr/src/bundle_installer.cpp.patch
"""

import argparse
import os
import re
import sys


PLACEHOLDER_RE = re.compile(r'^@@ -xxx', re.MULTILINE)


def find_patches(root):
    for base in ('aosp_patches', 'ohos_patches'):
        base_dir = os.path.join(root, base)
        if not os.path.isdir(base_dir):
            continue
        for dirpath, _, filenames in os.walk(base_dir):
            # skip the build.bk historical archive
            if 'build.bk' in dirpath.split(os.sep):
                continue
            for f in filenames:
                if f.endswith('.patch'):
                    yield os.path.join(dirpath, f)


def is_placeholder(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as fh:
            content = fh.read()
    except OSError as e:
        return None, str(e)
    if PLACEHOLDER_RE.search(content):
        return True, None
    return False, None


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--root',
                    default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    help='Adapter project root (default: parent of this script)')
    ap.add_argument('--quiet', '-q', action='store_true',
                    help='Only print placeholders, not all patches')
    args = ap.parse_args()

    placeholders = []
    total = 0
    for patch in sorted(find_patches(args.root)):
        total += 1
        is_ph, err = is_placeholder(patch)
        if err:
            print(f"ERROR reading {patch}: {err}", file=sys.stderr)
            continue
        rel = os.path.relpath(patch, args.root).replace('\\', '/')
        if is_ph:
            placeholders.append(rel)
            print(f"PLACEHOLDER  {rel}")
        elif not args.quiet:
            print(f"OK           {rel}")

    print()
    print(f"Total .patch files scanned: {total}")
    print(f"Placeholders detected:      {len(placeholders)}")

    if placeholders:
        print()
        print("These patches cannot be applied via `patch -p1`. They must be")
        print("rewritten with real line numbers from the OH source tree on ECS.")
        print("See FINALIZATION INSTRUCTIONS at the bottom of each patch file,")
        print("and doc/build_patch_log.html appendix A.3 for the full procedure.")
        return 1

    print("All patches have real line numbers — none are placeholders.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
