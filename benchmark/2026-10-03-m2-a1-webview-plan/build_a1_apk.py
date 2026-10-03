#!/usr/bin/env python3
"""Build the A1 WebView test APK (org.westlake.a1webview; test-only, never part of a generation).

    build_a1_apk.py   -> build/a1webview.apk  (built twice; the two must be byte-identical)

Pure Java — a real android.webkit.WebView, NO app native lib (the route-a WebView provider is overlaid at window time:
oh-adapter-runtime.jar + cc-wiki shim/worker .so). Same pinned toolchain as the A0 build_apk.py (javac/d8 from build_u12,
android-34 android.jar; aapt2 link; fixed zip timestamps; zipalign -p 4; apksigner debug key). No NATIVE dict.
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
KEY = Path.home() / '.android/debug.keystore'
# apksigner/keytool must run on JDK 17 (default java here is 1.8, cannot read the PKCS12 debug keystore)
ENV = dict(os.environ, PATH=str(Path(r1.D8_JAVA).parent) + os.pathsep + os.environ['PATH'])


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def build(work, out):
    if work.exists():
        shutil.rmtree(work)
    (work / 'cls').mkdir(parents=True)
    (work / 'dex').mkdir()
    subprocess.run([str(BT / 'aapt2'), 'link', '-o', str(work / 'base.apk'), '-I', str(r1.AJ), '--manifest',
                    str(HERE / 'src/java/AndroidManifest.xml')], check=True)
    subprocess.run([r1.pinned_javac(), '-source', '8', '-target', '8', '-nowarn', '-cp', str(r1.AJ), '-d',
                    str(work / 'cls'),
                    str(HERE / 'src/java/org/westlake/a1webview/MainActivity.java')], check=True)
    subprocess.run([str(r1.D8_JAVA), '-cp', str(r1.T / 'd8.jar'), 'com.android.tools.r8.D8', '--min-api', '28', '--lib',
                    str(r1.AJ), '--output', str(work / 'dex'),
                    *map(str, sorted((work / 'cls').rglob('*.class')))], check=True)
    entries = []
    with zipfile.ZipFile(work / 'base.apk') as z:
        entries = [(i.filename, z.read(i.filename)) for i in z.infolist()]
    entries.append(('classes.dex', (work / 'dex/classes.dex').read_bytes()))
    unaligned = work / 'unaligned.apk'
    with zipfile.ZipFile(unaligned, 'w') as z:
        for name, data in entries:
            zi = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_STORED if name.endswith('.arsc') else zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data)
    aligned = work / 'aligned.apk'
    subprocess.run([str(BT / 'zipalign'), '-f', '-p', '4', str(unaligned), str(aligned)], check=True)
    subprocess.run([str(BT / 'apksigner'), 'sign', '--ks', str(KEY), '--ks-pass', 'pass:android', '--key-pass',
                    'pass:android', '--ks-key-alias', 'androiddebugkey', '--out', str(out), str(aligned)], check=True,
                   env=ENV)
    shutil.rmtree(work)
    return sha(out)


if __name__ == '__main__':
    (HERE / 'build').mkdir(exist_ok=True)
    s1 = build(HERE / 'build/apk-w1', HERE / 'build/a1webview.apk')
    s2 = build(HERE / 'build/apk-w2', HERE / 'build/a1webview-check.apk')
    (HERE / 'build/a1webview-check.apk').unlink()
    v = subprocess.run([str(BT / 'apksigner'), 'verify', '--print-certs', str(HERE / 'build/a1webview.apk')],
                       capture_output=True, text=True, env=ENV)
    print(v.stdout.strip().splitlines()[0] if v.stdout else v.stderr)
    print('a1webview.apk sha256', s1, 'DETERMINISTIC', 'YES' if s1 == s2 else 'NO ' + s2)
    sys.exit(0 if s1 == s2 and v.returncode == 0 else 1)
