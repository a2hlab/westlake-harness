#!/usr/bin/env python3
"""G3 gate: report duplicate class names across the boot class path (BCP) jars.

A class defined in more than one BCP jar means the boot image carries two definitions
of the same type -- a red flag for a dex2oat-once boot-image build. Known-acceptable
duplicates (present in the accepted v3c/T5c image) live in an allow-list; anything
else is a violation and the gate exits non-zero.

Context (board #95, T7C-CHECKSYSTEMCLASS.md): the T7c `CheckSystemClass` abort turned
out to be an image/jar **checksum** mismatch, NOT a duplicate class -- this gate is
exactly what ruled the name-collision theory out (366acc27 added no new BCP duplicate).
It stays as a cheap pre-build guard so a future stubs change that DOES collide with a
framework/core class is caught before it ever reaches the board.

Inputs (one of):
  --framework-dir DIR   directory holding the BCP jars as <name>.jar
  --jars A.jar B.jar    explicit jar paths
  --classmap FILE       JSON {jar: [class,...]} -- deterministic replay/test input
Allow-list: --allow FILE (JSON list of FQCNs); defaults to the built-in v3c list.

Class names are internal form, e.g. android/net/NetworkInfo (no L...; wrapper).
Exit 0 = only allowed duplicates (or none); 1 = at least one unexpected duplicate;
2 = bad input.
"""
import argparse
import json
import struct
import sys
import zipfile
from pathlib import Path

# The nine boot-classpath jars, in BCP order (adapter-mainline-stubs is the T7 stubs jar).
BCP_JARS = ['core-oj', 'core-libart', 'core-icu4j', 'okhttp', 'bouncycastle',
            'apache-xml', 'framework', 'oh-adapter-framework', 'adapter-mainline-stubs']

# Duplicates already present in the accepted v3c/T5c boot image: framework *Initializer
# classes that the stubs jar also declares. They pass CheckSystemClass, so they are
# allowed. (Derived in T7C-CHECKSYSTEMCLASS.md: stubs_v3c INTERSECT bcp_union.)
DEFAULT_ALLOW = [
    'android/app/blob/BlobStoreManagerFrameworkInitializer',
    'android/app/job/JobSchedulerFrameworkInitializer',
    'android/content/rollback/RollbackManagerFrameworkInitializer',
    'android/media/MediaFrameworkPlatformInitializer',
    'android/nfc/NfcFrameworkInitializer',
    'android/provider/DeviceConfigInitializer',
    'android/telephony/TelephonyFrameworkInitializer',
]


# --- minimal dex class_defs parser (no external tools; see T7C-CHECKSYSTEMCLASS.md) ---
def _uleb128(b, o):
    result = shift = 0
    while True:
        byte = b[o]
        o += 1
        result |= (byte & 0x7f) << shift
        if byte < 0x80:
            return result, o
        shift += 7


def classes_in_dex(data):
    """Set of internal class names (foo/Bar) defined in one classes*.dex blob."""
    if data[:4] != b'dex\n':
        raise ValueError('not a dex file (bad magic)')
    string_ids_size, string_ids_off = struct.unpack_from('<II', data, 56)
    _type_ids_size, type_ids_off = struct.unpack_from('<II', data, 64)
    class_defs_size, class_defs_off = struct.unpack_from('<II', data, 96)

    def get_string(idx):
        if idx >= string_ids_size:
            raise ValueError('string index out of range')
        off = struct.unpack_from('<I', data, string_ids_off + idx * 4)[0]
        _n, p = _uleb128(data, off)  # MUTF-8 length in utf16 units; bytes end at NUL
        end = data.index(b'\x00', p)
        return data[p:end].decode('utf-8', 'replace')

    out = set()
    for i in range(class_defs_size):
        class_idx = struct.unpack_from('<I', data, class_defs_off + i * 32)[0]
        str_idx = struct.unpack_from('<I', data, type_ids_off + class_idx * 4)[0]
        desc = get_string(str_idx)
        if desc.startswith('L') and desc.endswith(';'):
            out.add(desc[1:-1])
    return out


def classes_in_jar(path):
    out = set()
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if name.endswith('.dex'):
                out |= classes_in_dex(z.read(name))
    return out


def build_classmap_from_dir(framework_dir, jars=BCP_JARS):
    classmap = {}
    for j in jars:
        p = Path(framework_dir) / (j + '.jar')
        if p.is_file():
            classmap[j] = sorted(classes_in_jar(p))
    return classmap


# --- pure gate logic (no dex needed; unit-tested directly) ---
def find_duplicates(jar_classes, allow):
    """jar_classes: {jar: iterable of FQCNs}. Returns a sorted list of
    (fqcn, [jars sorted], allowed_bool) for every class defined in >1 jar."""
    allow = set(allow)
    seen = {}
    for jar, classes in jar_classes.items():
        for c in classes:
            seen.setdefault(c, set()).add(jar)
    dups = [(c, sorted(jars), c in allow) for c, jars in seen.items() if len(jars) > 1]
    dups.sort()
    return dups


def report(dups, out=sys.stdout):
    violations = 0
    for c, jars, allowed in dups:
        tag = 'ok(allowed)' if allowed else 'DUPLICATE-VIOLATION'
        if not allowed:
            violations += 1
        print(f'{tag} {c} in {",".join(jars)}', file=out)
    print(f'bcp-duplicates: {len(dups)} duplicate class(es), {violations} violation(s)', file=out)
    return violations


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument('--framework-dir', help='directory with the BCP jars as <name>.jar')
    src.add_argument('--jars', nargs='+', help='explicit jar paths')
    src.add_argument('--classmap', type=Path, help='JSON {jar: [class,...]} deterministic input')
    ap.add_argument('--allow', type=Path, help='JSON list of allowed-duplicate FQCNs (default: built-in v3c list)')
    ap.add_argument('--json', action='store_true', help='machine-readable output')
    a = ap.parse_args(argv)

    allow = json.loads(a.allow.read_text()) if a.allow else DEFAULT_ALLOW
    try:
        if a.classmap:
            classmap = json.loads(a.classmap.read_text())
        elif a.jars:
            classmap = {Path(j).stem: sorted(classes_in_jar(j)) for j in a.jars}
        else:
            classmap = build_classmap_from_dir(a.framework_dir)
            if not classmap:
                print('no BCP jars found in ' + a.framework_dir, file=sys.stderr)
                return 2
    except (OSError, ValueError, zipfile.BadZipFile) as e:
        print(f'input error: {e}', file=sys.stderr)
        return 2

    dups = find_duplicates(classmap, allow)
    violations = sum(1 for _, _, allowed in dups if not allowed)
    if a.json:
        print(json.dumps({
            'jars': sorted(classmap),
            'duplicates': [{'class': c, 'jars': j, 'allowed': al} for c, j, al in dups],
            'violations': violations,
        }, indent=2))
    else:
        report(dups)
    return 1 if violations else 0


if __name__ == '__main__':
    sys.exit(main())
