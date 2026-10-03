#!/usr/bin/env python3
"""Build the A0 probe test APK (org.westlake.a0probe; test-only, never part of a generation).

    build_apk.py   -> build/a0probe.apk  (built twice; the two must be byte-identical)

Java: src/java/org/westlake/a0probe/MainActivity.java with the pinned javac and d8 of build_u12.py (android-34
android.jar). Manifest: src/java/AndroidManifest.xml via aapt2 link (build-tools 34.0.0). Native: build/native/
liba0shim.so + liba0probe.so (from build_a0_hw248.sh, hashes checked) as lib/arm64-v8a/. Zip entries get a fixed
timestamp; zipalign -p 4; apksigner with the local Android debug key (the test APK has no trust claim).
"""
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-02-u12-jar-plan'))
import build_u12 as r1  # noqa: E402

BT = Path.home() / 'Library/Android/sdk/build-tools/34.0.0'
NATIVE = {'liba0probe.so': '355ac614dd1df6c728b8eef758c71e53a009376d30fb9afbd143ee2b2a3a1191',
          'liba0shim.so': 'b15da15f5c8d1b3ae7cb1dc566b80707e782262c01438a9893ade94755796bbe'}
KEY = Path.home() / '.android/debug.keystore'
# apksigner/keytool must run on JDK 17: the default java here is 1.8.0_151, which cannot read the PKCS12 debug keystore
ENV = dict(os.environ, PATH=str(Path(r1.D8_JAVA).parent) + os.pathsep + os.environ['PATH'])


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(work, out):
    if work.exists():
        shutil.rmtree(work)
    (work / 'cls').mkdir(parents=True)
    (work / 'dex').mkdir()
    for n, h in NATIVE.items():
        assert sha(HERE / 'build/native' / n) == h, n
    subprocess.run([str(BT / 'aapt2'), 'link', '-o', str(work / 'base.apk'), '-I', str(r1.AJ), '--manifest',
                    str(HERE / 'src/java/AndroidManifest.xml')], check=True)
    subprocess.run([r1.pinned_javac(), '-source', '8', '-target', '8', '-nowarn', '-cp', str(r1.AJ), '-d', str(work / 'cls'),
                    str(HERE / 'src/java/org/westlake/a0probe/MainActivity.java')], check=True)
    subprocess.run([str(r1.D8_JAVA), '-cp', str(r1.T / 'd8.jar'), 'com.android.tools.r8.D8', '--min-api', '28', '--lib',
                    str(r1.AJ), '--output', str(work / 'dex'), *map(str, sorted((work / 'cls').rglob('*.class')))], check=True)
    entries = []
    with zipfile.ZipFile(work / 'base.apk') as z:
        entries = [(i.filename, z.read(i.filename)) for i in z.infolist()]
    entries.append(('classes.dex', (work / 'dex/classes.dex').read_bytes()))
    for n in sorted(NATIVE):
        entries.append(('lib/arm64-v8a/' + n, (HERE / 'build/native' / n).read_bytes()))
    unaligned = work / 'unaligned.apk'
    with zipfile.ZipFile(unaligned, 'w') as z:
        for name, data in entries:
            zi = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_STORED if name.endswith(('.so', '.arsc')) else zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data)
    aligned = work / 'aligned.apk'
    subprocess.run([str(BT / 'zipalign'), '-f', '-p', '4', str(unaligned), str(aligned)], check=True)
    subprocess.run([str(BT / 'apksigner'), 'sign', '--ks', str(KEY), '--ks-pass', 'pass:android', '--key-pass',
                    'pass:android', '--ks-key-alias', 'androiddebugkey', '--out', str(out), str(aligned)], check=True, env=ENV)
    shutil.rmtree(work)
    return sha(out)


if __name__ == '__main__':
    s1 = build(HERE / 'build/apk-w1', HERE / 'build/a0probe.apk')
    s2 = build(HERE / 'build/apk-w2', HERE / 'build/a0probe-check.apk')
    (HERE / 'build/a0probe-check.apk').unlink()
    v = subprocess.run([str(BT / 'apksigner'), 'verify', '--print-certs', str(HERE / 'build/a0probe.apk')],
                       capture_output=True, text=True, env=ENV)
    print(v.stdout.strip().splitlines()[0] if v.stdout else v.stderr)
    print('a0probe.apk sha256', s1, 'DETERMINISTIC', 'YES' if s1 == s2 else 'NO ' + s2)
    sys.exit(0 if s1 == s2 and v.returncode == 0 else 1)
