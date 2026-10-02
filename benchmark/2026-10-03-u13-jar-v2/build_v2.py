#!/usr/bin/env python3
"""U13 JAR v2 = U13 JAR 6790d500 (U12 r2 + theme probe + webkit glue) + adapter.activity.TelephonyRegistryStub.

    build_v2.py

One class, one smali needle: B7BindFixes, right after TelephonyServiceNames.install() (which itself follows
SystemServiceFetcherStubs.install(), where TelephonyFetcher seeds "phone"/"isub"): TelephonyRegistryStub.install().
Same pinned toolchain as build_u12.py; built twice, must be byte-identical.
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
NEEDLE = ('adapter/activity/B7BindFixes.smali',
          '    invoke-static {}, Ladapter/activity/TelephonyServiceNames;->install()V\n',
          '\n    invoke-static {}, Ladapter/activity/TelephonyRegistryStub;->install()V\n')


def main():
    b = r1.sha(BASE)
    assert b.startswith(BASE_SHA), f'base is not U13 JAR 6790d500: {b}'
    r1.BASE = BASE
    r1.SRCS = [HERE / 'src/adapter/activity/TelephonyRegistryStub.java']
    r1.NEEDLES = [NEEDLE]
    out = HERE / 'build/oh-adapter-runtime-u13-v2.jar'
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
