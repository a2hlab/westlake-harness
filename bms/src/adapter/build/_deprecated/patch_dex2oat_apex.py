#!/usr/bin/env python3
"""
Batch patch apex_available in AOSP Android.bp files for dex2oat host compilation.
Adds "//apex_available:platform" to all ART APEX module definitions.

Usage:
    python3 patch_dex2oat_apex.py [--aosp-root PATH] [--revert]
"""

import os
import sys
import glob
import argparse

PATTERNS = [
    (
        '        "com.android.art",\n        "com.android.art.debug",\n    ],',
        '        "com.android.art",\n        "com.android.art.debug",\n        "//apex_available:platform",\n    ],'
    ),
    (
        '        "com.android.art",\n        "com.android.art.debug",\n        "test_broken_com.android.art",\n    ],',
        '        "com.android.art",\n        "com.android.art.debug",\n        "test_broken_com.android.art",\n        "//apex_available:platform",\n    ],'
    ),
    (
        '        "com.android.art.debug",\n    ],',
        '        "com.android.art.debug",\n        "//apex_available:platform",\n    ],'
    ),
    (
        '        "com.android.i18n",\n    ],',
        '        "com.android.i18n",\n        "//apex_available:platform",\n    ],'
    ),
]

SCAN_DIRS = [
    "art",
    "libcore",
    "external/tinyxml2",
    "external/lzma",
    "external/libcap",
    "external/apache-xml",
    "external/bouncycastle",
    "external/okhttp",
    "external/icu",
    "external/lz4",
    "external/zlib",
    "external/fmtlib",
    "external/vixl",
    "external/dlmalloc",
    "external/libcxx",
    "external/libcxxabi",
    "external/expat",
    "external/googletest",
    "external/protobuf",
    "external/boringssl",
    "external/sqlite",
    "external/jsoncpp",
    "system/extras/libprocinfo",
    "external/rust/crates/rustc-demangle-capi",
]


def patch_file(filepath, revert=False):
    with open(filepath, 'r') as f:
        content = f.read()

    if revert:
        if '"//apex_available:platform"' not in content:
            return False
        content = content.replace('        "//apex_available:platform",\n', '')
        with open(filepath, 'w') as f:
            f.write(content)
        return True

    if '"//apex_available:platform"' in content:
        return False

    changed = False
    for old, new in PATTERNS:
        if old in content:
            content = content.replace(old, new)
            changed = True

    if changed:
        with open(filepath, 'w') as f:
            f.write(content)
    return changed


def main():
    parser = argparse.ArgumentParser(description='Patch apex_available for dex2oat build')
    parser.add_argument('--aosp-root', default=os.path.expanduser('~/aosp'))
    parser.add_argument('--revert', action='store_true', help='Remove platform patches')
    args = parser.parse_args()

    patched = 0
    skipped = 0

    for scan_dir in SCAN_DIRS:
        full_dir = os.path.join(args.aosp_root, scan_dir)
        if not os.path.isdir(full_dir):
            continue
        for bp in glob.glob(os.path.join(full_dir, '**', 'Android.bp'), recursive=True):
            if patch_file(bp, args.revert):
                rel = os.path.relpath(bp, args.aosp_root)
                action = "Reverted" if args.revert else "Patched"
                print(f"  {action}: {rel}")
                patched += 1
            else:
                skipped += 1

    # Also patch libcore/JavaLibrary.bp
    jlbp = os.path.join(args.aosp_root, 'libcore', 'JavaLibrary.bp')
    if os.path.exists(jlbp):
        if patch_file(jlbp, args.revert):
            action = "Reverted" if args.revert else "Patched"
            print(f"  {action}: libcore/JavaLibrary.bp")
            patched += 1

    action = "Reverted" if args.revert else "Patched"
    print(f"\n{action}: {patched} files, Skipped: {skipped} files")


if __name__ == '__main__':
    main()
