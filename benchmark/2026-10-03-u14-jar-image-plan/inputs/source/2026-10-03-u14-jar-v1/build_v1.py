#!/usr/bin/env python3
"""U14 JAR v1 = U13 JAR v3 bbc3f530 + adapter.activity.InProcessBindOrder (termux: in-process bind before RESUMED).

    build_v1.py

The class is fac7afbacd's (benchmark/2026-10-03-termux-and-u12-jar-check/src, unchanged). One smali needle in
ActivityManagerBindProxy.postInProcessBind, right after the in-process bind runnable is constructed:
`v1 = InProcessBindOrder.wrap(v1, connection)`; the existing Handler.post(v1) is unchanged. Same pinned toolchain as
build_u12.py / build_v3.py. After the build the output is disassembled again and every smali file other than the needle
file and the added classes must be byte-identical to the base's; built twice, must be byte-identical.
"""
import filecmp
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-02-u12-jar-plan'))
sys.path.insert(0, str(HERE.parents[1] / 'scripts/lab'))
import build_u12 as r1  # noqa: E402
import lab_paths  # noqa: E402

BASE = lab_paths.inputs() / 'generations/u13-jar-v3/oh-adapter-runtime-u13-v3.jar'
BASE_SHA = 'bbc3f530190f'
NEEDLE_FILE = 'adapter/activity/ActivityManagerBindProxy.smali'
NEEDLE = (NEEDLE_FILE,
          '    invoke-direct {v1, p0, p2, p1, p3}, Ladapter/activity/ActivityManagerBindProxy$1;-><init>('
          'Ladapter/activity/ActivityManagerBindProxy;Landroid/content/ComponentName;Landroid/content/Intent;'
          'Ljava/lang/Object;)V\n',
          '\n    invoke-static {v1, p3}, Ladapter/activity/InProcessBindOrder;->wrap(Ljava/lang/Runnable;'
          'Ljava/lang/Object;)Ljava/lang/Runnable;\n\n    move-result-object v1\n')
OUT = HERE / 'build/oh-adapter-runtime-u14-v1.jar'


def smali(jar, dst):
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    zipfile.ZipFile(jar).extract('classes.dex', dst)
    subprocess.run(['java', '-cp', r1.BAK_CP, 'org.jf.baksmali.Main', 'disassemble', str(dst / 'classes.dex'),
                    '-o', str(dst / 'smali')], check=True)
    return {str(p.relative_to(dst / 'smali')): p for p in (dst / 'smali').rglob('*.smali')}


def main():
    b = r1.sha(BASE)
    assert b.startswith(BASE_SHA), f'base is not U13 JAR v3 bbc3f530: {b}'
    r1.BASE = BASE
    r1.SRCS = [HERE / 'src/adapter/activity/InProcessBindOrder.java']
    r1.NEEDLES = [NEEDLE]
    s1, added = r1.build(HERE / 'build/w1', OUT)
    s2, _ = r1.build(HERE / 'build/w2', HERE / 'build/check.jar')
    (HERE / 'build/check.jar').unlink()
    for w in ('w1', 'w2'):
        shutil.rmtree(HERE / 'build' / w)
    base = smali(BASE, HERE / 'build/cmp-base')
    new = smali(OUT, HERE / 'build/cmp-new')
    changed = sorted(k for k in base if k in new and not filecmp.cmp(base[k], new[k], shallow=False))
    dropped = sorted(set(base) - set(new))
    extra = sorted(set(new) - set(base))
    for d in ('cmp-base', 'cmp-new'):
        shutil.rmtree(HERE / 'build' / d)
    print('classes added:', ', '.join(added))
    print('smali vs base: changed', changed, 'dropped', dropped, 'added', extra)
    assert changed == [NEEDLE_FILE], changed
    assert not dropped and sorted(extra) == sorted(added), (dropped, extra)
    print('sha256', s1, 'DETERMINISTIC', 'YES' if s1 == s2 else 'NO ' + s2)
    return 0 if s1 == s2 else 1


if __name__ == '__main__':
    sys.exit(main())
