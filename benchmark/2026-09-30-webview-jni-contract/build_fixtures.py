#!/usr/bin/env python3
"""Build tiny real DEX test inputs, never production jars. Run through dockbuild."""
import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

P = Path(__file__).resolve().parent
SUPPLIER = '''.class public Ladapter/core/WebViewUpdateServiceAdapter;
.super Ljava/lang/Object;
.method public static isAvailable()Z
 .registers 1
 const/4 v0, 0x0
 return v0
.end method
.method public static getInstance()Ladapter/core/WebViewUpdateServiceAdapter;
 .registers 1
 const/4 v0, 0x0
 return-object v0
.end method
'''
CALLER = '''.class public Ladapter/core/WestlakeWebViewInstall;
.super Ljava/lang/Object;
.method private static native nativePrime()Z
.end method
.method private static native nativePublishAfterBind()Z
.end method
'''
REFERENCE = '''.class public Lfixture/ReferenceOnly;
.super Ljava/lang/Object;
.field public static final NAME:Ljava/lang/String; = "adapter/core/WebViewUpdateServiceAdapter"
.method public static touch()Z
 .registers 1
 invoke-static {}, Ladapter/core/WebViewUpdateServiceAdapter;->isAvailable()Z
 move-result v0
 return v0
.end method
'''


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--inputs', type=Path, required=True)
    a = ap.parse_args()
    cp = ':'.join(str(p) for p in sorted(a.inputs.glob('*.jar')) if p.name not in ('android.jar', 'd8.jar') and not p.name.startswith('baseline'))
    fixtures = P / 'fixtures'; fixtures.mkdir(exist_ok=False)
    variants = {
        'good': [[SUPPLIER, CALLER]],
        'reference-only': [[REFERENCE, CALLER]],
        'wrong-return': [[SUPPLIER.replace('getInstance()Ladapter/core/WebViewUpdateServiceAdapter;', 'getInstance()Landroid/os/IBinder;'), CALLER]],
        'nonstatic': [[SUPPLIER.replace('static isAvailable', 'isAvailable'), CALLER]],
        'not-native': [[SUPPLIER, CALLER.replace('private static native nativePrime()Z\n.end method', 'private static nativePrime()Z\n .registers 1\n const/4 v0, 0x0\n return v0\n.end method')]],
        'multidex': [[CALLER], [SUPPLIER]],
        'duplicate': [[CALLER, SUPPLIER], [SUPPLIER]],
        'inherited': [[SUPPLIER.replace('Ladapter/core/WebViewUpdateServiceAdapter;', 'Lfixture/Parent;', 1), CALLER,
                        '.class public Ladapter/core/WebViewUpdateServiceAdapter;\n.super Lfixture/Parent;\n']],
    }
    receipts = {}
    for name, groups in variants.items():
        out = fixtures / name; out.mkdir()
        jar = fixtures / (name + '.jar')
        with zipfile.ZipFile(jar, 'w') as z:
            for index, bodies in enumerate(groups):
                tree = out / str(index); tree.mkdir()
                for n, body in enumerate(bodies): (tree / f'{n}.smali').write_text(body)
                dex = out / (str(index) + '.dex')
                subprocess.run(['java', '-cp', cp, 'org.jf.smali.Main', 'assemble', str(tree), '-o', str(dex)], check=True)
                info = zipfile.ZipInfo('classes' + (str(index+1) if index else '') + '.dex', (2026, 9, 30, 0, 0, 0))
                z.writestr(info, dex.read_bytes())
        receipts[name] = {'sha256': hashlib.sha256(jar.read_bytes()).hexdigest(), 'bytes': jar.stat().st_size}
    (P / 'fixture-receipt.json').write_text(json.dumps({'test_only': True, 'fixtures': receipts,
        'inputs': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in a.inputs.glob('*.jar') if p.name.startswith(('smali','baksmali','dexlib','guava','jcommander','util'))}}, indent=2)+'\n')


if __name__ == '__main__': main()
