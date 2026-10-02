#!/usr/bin/env python3
"""Which of the 166 keys carry androidx.webkit, and which call an ALGORITHMIC_DARKENING setter after a feature check?

    webkit_scan.py [--out webkit-scan.csv]

Per frozen APK (B10 collect.inputs), dexdump -d every classes*.dex and record:
  androidx_webkit      the APK bundles androidx.webkit (the support-library boundary interface
                       org/chromium/support_lib_boundary/WebkitToCompatConverterBoundaryInterface is referenced)
  feature_checks       const-string "ALGORITHMIC_DARKENING" sites OUTSIDE androidx.webkit's feature table class
                       (= app code passing the name to WebViewFeature.isFeatureSupported)
  darkening_setters    invoke sites of the class/method that throws through the feature's isSupportedByWebView
                       (found structurally: the static (Landroid/webkit/WebSettings;Z)V methods whose body is
                       `feature.b(); if-eqz -> <x>.a()Ljava/lang/UnsupportedOperationException; throw`)
On our stack isFeatureSupported(ALGORITHMIC_DARKENING) is true (framework SDK_INT >= 33) while the setter checks the
WebView support-library feature list, which is empty (no org.chromium.support_lib_glue in the provider's loader), so
every app with feature_checks > 0 and a reachable setter throws UnsupportedOperationException like privacybrowser.
"""
import argparse
import csv
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
sys.path.insert(0, str(REPO / 'benchmark/2026-10-01-b10-theme-graphics'))
import collect  # noqa: E402
import lab_paths  # noqa: E402

DD = str(sorted((Path.home() / 'Library/Android/sdk/build-tools').glob('*/dexdump'))[-1])


def scan(apk):
    out = {'androidx_webkit': False, 'feature_checks': 0, 'darkening_setters': 0, 'setter_methods': ''}
    with tempfile.TemporaryDirectory() as d, zipfile.ZipFile(apk) as z:
        dumps = []
        for n in z.namelist():
            if re.fullmatch(r'classes\d*\.dex', n):
                p = Path(d) / n
                p.write_bytes(z.read(n))
                dumps.append(subprocess.run([DD, '-d', str(p)], capture_output=True, text=True,
                                            errors='replace').stdout)
    text = '\n'.join(dumps)
    out['androidx_webkit'] = 'support_lib_boundary/WebkitToCompatConverterBoundaryInterface' in text
    if not out['androidx_webkit']:
        return out
    # split into methods: header lines "[addr] cls.meth:sig"
    methods = re.split(r'\n(?=[0-9a-f]{6}:\s+\|\[[0-9a-f]+\] )', text)
    table_classes, setters = set(), set()
    for m in methods:
        h = re.match(r'[0-9a-f]{6}:\s+\|\[[0-9a-f]+\] (\S+?)\.([^.:]+):(\S+)', m)
        if not h:
            continue
        cls, name, sig = h.groups()
        if '"ALGORITHMIC_DARKENING"' in m and name == '<init>':
            table_classes.add(cls)
    for m in methods:
        h = re.match(r'[0-9a-f]{6}:\s+\|\[[0-9a-f]+\] (\S+?)\.([^.:]+):(\S+)', m)
        if not h:
            continue
        cls, name, sig = h.groups()
        if sig == '(Landroid/webkit/WebSettings;Z)V' and 'Ljava/lang/UnsupportedOperationException;' in m \
                and 'throw' in m and re.search(r'invoke-virtual \{v\d+\}, L[^;]+;\.b:\(\)Z', m):
            setters.add(f'{cls}.{name}')
    for m in methods:
        h = re.match(r'[0-9a-f]{6}:\s+\|\[[0-9a-f]+\] (\S+?)\.([^.:]+):(\S+)', m)
        if not h:
            continue
        cls, name, sig = h.groups()
        if '"ALGORITHMIC_DARKENING"' in m and cls not in table_classes and name not in ('<clinit>', '<init>'):
            out['feature_checks'] += m.count('"ALGORITHMIC_DARKENING"')
        for s in setters:
            c, n = s.rsplit('.', 1)
            out['darkening_setters'] += len(re.findall(rf'L{re.escape(c.replace(".", "/"))};\.{re.escape(n)}:\(Landroid/webkit/WebSettings;Z\)V', m))
    out['setter_methods'] = ' '.join(sorted(setters))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'webkit-scan.csv'))
    a = ap.parse_args()
    rows = []
    for r in collect.inputs(lab_paths.workspaces()):
        s = scan(r['path'])
        rows.append({'key': r['key'], **s})
    with open(a.out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    wk = [r for r in rows if r['androidx_webkit']]
    hit = [r for r in wk if r['feature_checks'] and r['darkening_setters']]
    print(f'keys {len(rows)}; bundle androidx.webkit {len(wk)}; ALGORITHMIC_DARKENING check + setter call {len(hit)}')
    for r in hit:
        print('  ', r['key'], 'checks', r['feature_checks'], 'setter calls', r['darkening_setters'], r['setter_methods'])
    return 0


if __name__ == '__main__':
    sys.exit(main())
