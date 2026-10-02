#!/usr/bin/env python3
"""Where does privacybrowser's UnsupportedOperationException come from: our jars or the app's own dex?

    first_frame.py [--out first-frame.txt]

Checks the deployed U10.1T8 jars the boards run (runtime 5ae3dd29, stubs 2f365a75, framework adapter 2257b835; plus
framework.jar and the U13 runtime 0482c9b1) and the APK's dex for: the first stack frames' classes (hi0, bi0, fi0;
R8-obfuscated androidx.webkit), the androidx.webkit boundary package, the support-library glue class, and the
exception message string.
"""
import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
sys.path.insert(0, str(REPO / 'benchmark/2026-10-02-toutiao-oldroute-diff'))
import java_classes  # noqa: E402
import lab_paths  # noqa: E402

G = lab_paths.inputs() / 'generations'
B = G / 'u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle'
JARS = {'runtime 5ae3dd29 (deployed)': B / 'framework/oh-adapter-runtime.jar',
        'stubs 2f365a75 (deployed, BCP)': B / 'framework/adapter-mainline-stubs.jar',
        'framework adapter 2257b835 (deployed, BCP)': B / 'native/payload/android/framework/oh-adapter-framework.jar',
        'framework.jar (deployed, BCP)': B / 'native/payload/android/framework/framework.jar',
        'runtime 0482c9b1 (U13)': G / 'u12r2-v1/oh-adapter-runtime-u12r2.jar'}
APK = lab_paths.inputs() / 'corpus-v2/apks/com.stoutner.privacybrowser.standard_81.apk'
CLASSES = ['Lhi0;', 'Lbi0;', 'Lfi0;', 'Lorg/chromium/support_lib_glue/SupportLibReflectionUtil;',
           'Lorg/chromium/support_lib_boundary/WebSettingsBoundaryInterface;', 'Landroid/webkit/WebViewFactoryProvider;']
MSG = b'This method is not supported by the current version of the framework and the current WebView APK'


def dexes(path):
    with zipfile.ZipFile(path) as z:
        return [z.read(n) for n in z.namelist() if n.startswith('classes') and n.endswith('.dex')]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'first-frame.txt'))
    a = ap.parse_args()
    lines = []
    for label, p in list(JARS.items()) + [('APK privacybrowser 81 (app dex)', APK)]:
        data = Path(p).read_bytes()
        defined = set()
        for d in dexes(p):
            defined |= java_classes.dex_defined(d) if hasattr(java_classes, 'dex_defined') else set()
        if not defined:
            defined = java_classes.jar_defined(data)
        msg = any(MSG in d for d in dexes(p))
        lines.append(f'{label} sha {hashlib.sha256(data).hexdigest()[:8]}: '
                     + ', '.join(f'{c}={"yes" if c in defined else "no"}' for c in CLASSES) + f', message={"yes" if msg else "no"}')
    Path(a.out).write_text('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    return 0


if __name__ == '__main__':
    sys.exit(main())
