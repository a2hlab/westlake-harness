#!/usr/bin/env python3
"""Runtime-jar variants on top of the U13 runtime jar 0482c9b1 (= U12 r2): theme probe, androidx.webkit glue, both.

    build_walls2.py [probe|glue|both|all]

New files only, one smali needle each, same pinned toolchain and determinism check as build_u12.py (built twice,
must be byte-identical):
  probe: adapter.activity.ThemeProbe; needle in AppSchedulerBridge.ensureBindApplication, right after
         ProviderAuthorityRefs.resolve(bindData) (the Application exists there): ThemeProbe.install().
         Disabled unless OH parameter debug.westlake.theme_probe lists the package.
  glue:  org.chromium.support_lib_glue.SupportLibReflectionUtil + adapter.activity.WebkitSupportGlue; needle in
         J10eWebView.install, right after J10gWebExtras.install(): WebkitSupportGlue.install().
"""
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-02-u12-jar-plan'))
sys.path.insert(0, str(HERE.parents[1] / 'scripts/lab'))
import build_u12 as r1  # noqa: E402
import lab_paths  # noqa: E402

BASE = lab_paths.inputs() / 'generations/u12r2-v1/oh-adapter-runtime-u12r2.jar'
BASE_SHA = '0482c9b13fbc'
SRC = HERE / 'src'
PROBE = ([SRC / 'adapter/activity/ThemeProbe.java'],
         [('adapter/activity/AppSchedulerBridge.smali',
           '    invoke-static {v13}, Ladapter/activity/ProviderAuthorityRefs;->resolve(Ljava/lang/Object;)V\n',
           '\n    invoke-static {}, Ladapter/activity/ThemeProbe;->install()V\n')])
GLUE = ([SRC / 'org/chromium/support_lib_glue/SupportLibReflectionUtil.java',
         SRC / 'adapter/activity/WebkitSupportGlue.java'],
        [('adapter/activity/J10eWebView.smali',
          '    invoke-static {}, Ladapter/activity/J10gWebExtras;->install()V\n',
          '\n    invoke-static {}, Ladapter/activity/WebkitSupportGlue;->install()V\n')])
VARIANTS = {'probe': [PROBE], 'glue': [GLUE], 'both': [PROBE, GLUE]}


def build(name):
    srcs, needles = [], []
    for s, n in VARIANTS[name]:
        srcs += s
        needles += n
    r1.BASE = BASE
    r1.SRCS = srcs
    r1.NEEDLES = needles
    out = HERE / f'build/oh-adapter-runtime-u13-{name}.jar'
    s1, added = r1.build(HERE / f'build/{name}-1', out)
    s2, _ = r1.build(HERE / f'build/{name}-2', HERE / f'build/{name}-check.jar')
    (HERE / f'build/{name}-check.jar').unlink()
    for w in (f'{name}-1', f'{name}-2'):
        shutil.rmtree(HERE / 'build' / w)
    print(f'{name}: classes added {", ".join(added)}')
    print(f'{name}: sha256 {s1} DETERMINISTIC {"YES" if s1 == s2 else "NO " + s2}')
    return s1 == s2


if __name__ == '__main__':
    b = r1.sha(BASE)
    assert b.startswith(BASE_SHA), f'base is not 0482c9b1: {b}'
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    names = list(VARIANTS) if what == 'all' else [what]
    sys.exit(0 if all([build(n) for n in names]) else 1)
