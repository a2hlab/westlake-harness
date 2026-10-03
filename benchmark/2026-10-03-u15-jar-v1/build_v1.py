#!/usr/bin/env python3
"""U15 runtime JAR v1 = U14 JAR v1 0349eb83 + adapter.activity.TrampolineFinishOrder + the fd-api alias-theme order.

    build_v1.py

New class: src/adapter/activity/TrampolineFinishOrder.java (x trampoline hand-off, 2026-10-03-x-trampoline-handover).
compile-only/ holds a stand-in for the hidden android.app.IActivityClientController (javac/d8 classpath only).
Four smali needles, nothing else edited:
  1. B7BindFixes, after OwnProviderLocal.install() (U12's needle, itself after ActivityManagerBindProxy.install()):
     TrampolineFinishOrder.install()  -- start observer over IActivityTaskManager.
  2. AppSchedulerBridge.nativeOnScheduleLaunchAbility, the controller handed to LaunchActivityItem.obtain:
     v39 = TrampolineFinishOrder.controller(ActivityClientControllerAdapter.getInstance()).
  3. AppSchedulerBridge.nativeOnScheduleLaunchAbility, first instruction: TrampolineFinishOrder.onLaunchAbility(bundle, ability).
  4. AppSchedulerBridge.nativeOnScheduleLaunchAbility, right after `if (sEnrichedTheme != 0) ai.theme = sEnrichedTheme`
     (source line 1748): AliasTargetTheme.apply(ai) again, so an alias keeps its target's theme (fd-api; the existing
     call at line 1644 is overwritten by line 1748).
Same pinned toolchain as build_u12.py / U14 build_v1.py. After the build the output is disassembled again and every
smali file other than the two needle files and the added classes must be byte-identical to the base's; built twice,
must be byte-identical.
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

BASE = lab_paths.inputs() / 'generations/u14-jar-v1/oh-adapter-runtime-u14-v1.jar'
BASE_SHA = '0349eb834e66'
ASB = 'adapter/activity/AppSchedulerBridge.smali'
TFO = 'Ladapter/activity/TrampolineFinishOrder;'
NEEDLES = [
    ('adapter/activity/B7BindFixes.smali',
     '    invoke-static {}, Ladapter/activity/OwnProviderLocal;->install()V\n',
     f'\n    invoke-static {{}}, {TFO}->install()V\n'),
    (ASB,
     '    invoke-static {}, Ladapter/activity/ActivityClientControllerAdapter;->getInstance()'
     'Ladapter/activity/ActivityClientControllerAdapter;\n\n    move-result-object v39\n',
     f'\n    invoke-static/range {{v39 .. v39}}, {TFO}->controller(Landroid/app/IActivityClientController;)'
     'Landroid/app/IActivityClientController;\n\n    move-result-object v39\n'),
    (ASB,
     '.method public static nativeOnScheduleLaunchAbility(Ljava/lang/Object;Ljava/lang/String;Ljava/lang/String;I'
     'Ljava/lang/String;Ljava/lang/String;J)V\n    .registers 53\n',
     f'\n    invoke-static/range {{p1 .. p2}}, {TFO}->onLaunchAbility(Ljava/lang/String;Ljava/lang/String;)V\n'),
    (ASB,
     '    iput v2, v4, Landroid/content/pm/ActivityInfo;->theme:I\n\n    :cond_34d\n',
     '    invoke-static {v4}, Ladapter/activity/AliasTargetTheme;->apply(Landroid/content/pm/ActivityInfo;)V\n\n'),
]
NEEDLE_FILES = sorted({n[0] for n in NEEDLES})
OUT = HERE / 'build/oh-adapter-runtime-u15-v1.jar'


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
    assert b.startswith(BASE_SHA), f'base is not U14 JAR v1 0349eb83: {b}'
    r1.BASE = BASE
    r1.SRCS = [HERE / 'src/adapter/activity/TrampolineFinishOrder.java']
    r1.COMPILE_ONLY = HERE / 'compile-only'
    r1.NEEDLES = NEEDLES
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
    gates = HERE / 'gates'
    gates.mkdir(exist_ok=True)
    for rel in changed:
        d = subprocess.run(['/usr/bin/diff', '-u', '--label', 'u14-v1/' + rel, '--label', 'u15-v1/' + rel,
                            str(base[rel]), str(new[rel])], capture_output=True, text=True).stdout
        (gates / ('needle-' + Path(rel).stem + '.diff')).write_text(d)
    for d in ('cmp-base', 'cmp-new'):
        shutil.rmtree(HERE / 'build' / d)
    print('classes added:', ', '.join(added))
    print('smali vs base: changed', changed, 'dropped', dropped, 'added', extra)
    assert changed == NEEDLE_FILES, changed
    assert not dropped and sorted(extra) == sorted(added), (dropped, extra)
    print('sha256', s1, 'DETERMINISTIC', 'YES' if s1 == s2 else 'NO ' + s2)
    return 0 if s1 == s2 else 1


if __name__ == '__main__':
    sys.exit(main())
