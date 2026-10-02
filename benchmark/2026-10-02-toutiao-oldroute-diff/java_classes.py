#!/usr/bin/env python3
"""Toutiao's framework class references against the old route's BCP and the current route-A BCP.

    java_classes.py [--out java-classes.csv]

Old BCP   = the 9 fw/*.jar inside the old delivery bundle tt-rt.tar ($HOME/a2hlab-provision/ttbundle, MANIFEST 7/7),
            read straight from the tar.
Current   = the 9 BCP jars of the T8 v3 package (native/payload/android/framework/ + the framework/ overlay for
            adapter-mainline-stubs), checked against window5 61b's boot-image-fingerprint.txt / runtime-fingerprint.txt.
            oh-adapter-runtime.jar is listed separately: it is not on the boot class path (runtime PathClassLoader),
            so an app class cannot resolve against it.
APK       = toutiao a1112a0c, all classes*.dex. A reference is a type_id the APK uses but does not define.
Writes one row per referenced platform type (java./javax./android./com.android./dalvik./libcore./org.apache./
org.json./org.xml./org.w3c./sun.) with present_old / present_new / present_runtime_only.
"""
import argparse
import csv
import hashlib
import io
import struct
import sys
import tarfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
sys.path.insert(0, str(REPO / 'benchmark/2026-10-02-android-net-stub-members'))
import lab_paths  # noqa: E402
import sweep  # noqa: E402

OLD_TAR = Path.home() / 'a2hlab-provision/ttbundle/tt-rt.tar'
OLD_TAR_SHA = '014c566e3813109e680c1361d6054adb181a7e3e9fb80d13d682faa161da847f'
V3 = lab_paths.inputs() / 'generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle'
NEW_BCP = {  # jar -> (path in the v3 package, sha256 prefix the board runs: window5 61b fingerprints)
    'core-oj': ('native/payload/android/framework/core-oj.jar', 'e5b187702b82'),
    'core-libart': ('native/payload/android/framework/core-libart.jar', '4e767490d696'),
    'okhttp': ('native/payload/android/framework/okhttp.jar', 'd510981adcb7'),
    'bouncycastle': ('native/payload/android/framework/bouncycastle.jar', '8b15216d690f'),
    'apache-xml': ('native/payload/android/framework/apache-xml.jar', 'f79af065bdd6'),
    'core-icu4j': ('native/payload/android/framework/core-icu4j.jar', 'f31e34e244b6'),
    'framework': ('native/payload/android/framework/framework.jar', '3e106350d882'),
    'oh-adapter-framework': ('native/payload/android/framework/oh-adapter-framework.jar', '2257b835afda'),
    'adapter-mainline-stubs': ('framework/adapter-mainline-stubs.jar', '2f365a75581b'),
}
NEW_RUNTIME = ('framework/oh-adapter-runtime.jar', '5ae3dd29d45c')
PLATFORM = ('Ljava/', 'Ljavax/', 'Landroid/', 'Lcom/android/', 'Ldalvik/', 'Llibcore/', 'Lorg/apache/', 'Lorg/json/',
            'Lorg/xml/', 'Lorg/w3c/', 'Lsun/')


def uleb(b, o):
    r = s = 0
    while True:
        x = b[o]
        o += 1
        r |= (x & 0x7f) << s
        if x < 0x80:
            return r, o
        s += 7


def dex_types(b):
    """(defined, referenced) type descriptors of one dex."""
    sid_size, sid_off, tid_size, tid_off = struct.unpack_from('<IIII', b, 0x38)
    cd_size, cd_off = struct.unpack_from('<II', b, 0x60)

    def string(i):
        off = struct.unpack_from('<I', b, sid_off + 4 * i)[0]
        _, o = uleb(b, off)
        e = b.index(0, o)
        return b[o:e].decode('utf-8', 'replace')
    types = [string(struct.unpack_from('<I', b, tid_off + 4 * i)[0]) for i in range(tid_size)]
    defined = {types[struct.unpack_from('<I', b, cd_off + 32 * i)[0]] for i in range(cd_size)}
    return defined, set(types)


def jar_defined(data):
    out = set()
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for n in z.namelist():
            if n.startswith('classes') and n.endswith('.dex'):
                out |= dex_types(z.read(n))[0]
    return out


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'java-classes.csv'))
    a = ap.parse_args()
    assert sha(OLD_TAR.read_bytes()) == OLD_TAR_SHA, 'tt-rt.tar is not the MANIFEST copy'
    old, old_where = set(), {}
    with tarfile.open(OLD_TAR) as t:
        for m in t.getmembers():
            p = m.name.lstrip('./')
            if p.startswith('fw/') and p.endswith('.jar'):
                d = t.extractfile(m).read()
                for c in jar_defined(d):
                    old.add(c)
                    old_where.setdefault(c, p[3:-4])
    new, new_where = set(), {}
    for j, (rel, pre) in NEW_BCP.items():
        d = (V3 / rel).read_bytes()
        assert sha(d).startswith(pre), f'{rel} is not the board copy {pre}'
        for c in jar_defined(d):
            new.add(c)
            new_where.setdefault(c, j)
    d = (V3 / NEW_RUNTIME[0]).read_bytes()
    assert sha(d).startswith(NEW_RUNTIME[1])
    runtime = jar_defined(d)
    apk = sweep.apks('toutiao')[0]
    app_def, app_ref = set(), set()
    with zipfile.ZipFile(apk) as z:
        for n in z.namelist():
            if n.startswith('classes') and n.endswith('.dex'):
                dd, rr = dex_types(z.read(n))
                app_def |= dd
                app_ref |= rr
    refs = sorted(t for t in app_ref - app_def if t.startswith(PLATFORM))
    rows = [{'type': t, 'present_old': int(t in old), 'old_jar': old_where.get(t, ''),
             'present_new': int(t in new), 'new_jar': new_where.get(t, ''),
             'runtime_jar_only': int(t not in new and t in runtime)} for t in refs]
    with open(a.out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    gap = [r for r in rows if r['present_old'] and not r['present_new']]
    gain = [r for r in rows if r['present_new'] and not r['present_old']]
    both = [r for r in rows if not r['present_old'] and not r['present_new']]
    print(f'old BCP {len(old)} classes, new BCP {len(new)}, runtime jar {len(runtime)}; APK {apk.name}: '
          f'{len(refs)} platform types referenced')
    print(f'old-only (gap) {len(gap)}, new-only {len(gain)}, in neither {len(both)}')
    by = {}
    for r in gap:
        k = '/'.join(r['type'].split('/')[:3])
        by[k] = by.get(k, 0) + 1
    print('gap by package:', sorted(by.items(), key=lambda x: -x[1])[:25])
    return 0


if __name__ == '__main__':
    sys.exit(main())
