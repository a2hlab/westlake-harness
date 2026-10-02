#!/usr/bin/env python3
"""Runtime jar = U13 JAR 6790d500 (probe + webkit glue) + adapter.activity.InProcessBindOrder, for U14.

    build_bindorder.py

One smali needle in ActivityManagerBindProxy.postInProcessBind, right after the in-process bind runnable is
constructed: `v1 = InProcessBindOrder.wrap(v1, connection)`; the existing Handler.post(v1) is unchanged. Same pinned
toolchain as build_u12.py; built twice, must be byte-identical.
"""
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-02-u12-jar-plan'))
sys.path.insert(0, str(HERE.parents[1] / 'scripts/lab'))
import build_u12 as r1  # noqa: E402
import lab_paths  # noqa: E402

BASE = lab_paths.inputs() / 'generations/u13-walls2-v1/oh-adapter-runtime-u13-both.jar'
BASE_SHA = '6790d5001d66'
NEEDLE = ('adapter/activity/ActivityManagerBindProxy.smali',
          '    invoke-direct {v1, p0, p2, p1, p3}, Ladapter/activity/ActivityManagerBindProxy$1;-><init>('
          'Ladapter/activity/ActivityManagerBindProxy;Landroid/content/ComponentName;Landroid/content/Intent;'
          'Ljava/lang/Object;)V\n',
          '\n    invoke-static {v1, p3}, Ladapter/activity/InProcessBindOrder;->wrap(Ljava/lang/Runnable;'
          'Ljava/lang/Object;)Ljava/lang/Runnable;\n\n    move-result-object v1\n')


def main():
    b = r1.sha(BASE)
    assert b.startswith(BASE_SHA), f'base is not U13 JAR 6790d500: {b}'
    r1.BASE = BASE
    r1.SRCS = [HERE / 'src/adapter/activity/InProcessBindOrder.java']
    r1.NEEDLES = [NEEDLE]
    out = HERE / 'build/oh-adapter-runtime-u14-bindorder.jar'
    s1, added = r1.build(HERE / 'build/w1', out)
    s2, _ = r1.build(HERE / 'build/w2', HERE / 'build/check.jar')
    (HERE / 'build/check.jar').unlink()
    for w in ('w1', 'w2'):
        shutil.rmtree(HERE / 'build' / w)
    print('classes added:', ', '.join(added))
    print('sha256', s1, 'DETERMINISTIC', 'YES' if s1 == s2 else 'NO ' + s2)
    return 0 if s1 == s2 else 1


if __name__ == '__main__':
    sys.exit(main())
