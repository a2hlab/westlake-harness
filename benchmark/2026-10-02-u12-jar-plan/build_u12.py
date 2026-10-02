#!/usr/bin/env python3
"""U12 runtime JAR = U11i (oh-adapter-runtime 5ae3dd29) + OwnProviderLocal (U11j) + upstream WlSettingsProvider path B.

New files only; two smali needles, no existing class edited except the two call sites:
  1. B7BindFixes, right after `ActivityManagerBindProxy.install()`: `OwnProviderLocal.install()` (exactly U11j's needle).
  2. AppSpawnXInit.preInitSettingsCache, right after its call to the hollowed
     `AppSpawnXInit.installSettingsContentProviderStub()`: `WlSettingsStub.installSettingsContentProviderStub()`.
Sources: ../2026-10-02-own-provider-local/src/OwnProviderLocal.java (unchanged), src/adapter/activity/WlSettingsProvider.java
(upstream blob 22911038, byte-identical) and src/adapter/activity/WlSettingsStub.java (upstream path B, verbatim).
compile-only/ holds a stand-in for the hidden ActivityThread.currentApplication(); it is on javac's classpath only.
Same toolchain as build_u11j.py (javac pinned, d8 on openjdk@17, baksmali/smali 2.5.2 with jcommander-1.64, `smali -j 1`,
fixed zip timestamps). Built twice; the two jars must be byte-identical.
"""
import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'scripts/lab'))
sys.path.insert(0, str(HERE.parent / '2026-10-02-own-provider-local'))
import lab_paths  # noqa: E402
from build_u11j import BAK_CP, SMALI_CP, AJ, D8_JAVA, T, BASE, BASE_SHA, pinned_javac, sha, run  # noqa: E402

SRCS = [HERE.parent / '2026-10-02-own-provider-local/src/OwnProviderLocal.java',
        HERE / 'src/adapter/activity/WlSettingsProvider.java',
        HERE / 'src/adapter/activity/WlSettingsStub.java']
COMPILE_ONLY = HERE / 'compile-only'
OUT = HERE / 'build/oh-adapter-runtime-u12.jar'
NEEDLES = [
    ('adapter/activity/B7BindFixes.smali',
     '    invoke-static {}, Ladapter/activity/ActivityManagerBindProxy;->install()V\n',
     '\n    invoke-static {}, Ladapter/activity/OwnProviderLocal;->install()V\n'),
    ('com/android/internal/os/AppSpawnXInit.smali',
     '    invoke-static {}, Lcom/android/internal/os/AppSpawnXInit;->installSettingsContentProviderStub()V\n',
     '\n    invoke-static {}, Ladapter/activity/WlSettingsStub;->installSettingsContentProviderStub()V\n'),
]


def build(work, out):
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    bj = work / 'basejar'
    with zipfile.ZipFile(BASE) as z:
        z.extractall(bj)
    base = work / 'smali'
    run(['java', '-cp', BAK_CP, 'org.jf.baksmali.Main', 'disassemble', bj / 'classes.dex', '-o', base])
    before = {str(p.relative_to(base)) for p in base.rglob('*.smali')}
    co = work / 'compile-only'
    co.mkdir()
    run([pinned_javac(), '-source', '8', '-target', '8', '-nowarn', '-cp', AJ, '-d', co,
         *sorted(COMPILE_ONLY.rglob('*.java'))])
    cc = work / 'classes'
    cc.mkdir()
    run([pinned_javac(), '-source', '8', '-target', '8', '-nowarn', '-cp', f'{AJ}:{co}', '-d', cc, *SRCS])
    dd = work / 'dex'
    dd.mkdir()
    run([D8_JAVA, '-cp', T / 'd8.jar', 'com.android.tools.r8.D8', '--min-api', '28', '--lib', AJ, '--classpath', co,
         '--output', dd, *sorted(cc.rglob('*.class'))])
    js = work / 'js'
    run(['java', '-cp', BAK_CP, 'org.jf.baksmali.Main', 'disassemble', dd / 'classes.dex', '-o', js])
    added = []
    for p in sorted(js.rglob('*.smali')):
        rel = p.relative_to(js)
        assert str(rel) not in before, f'{rel} already in the base jar'
        assert not str(rel).startswith('android/'), f'{rel}: a compile-only stand-in leaked into the dex'
        (base / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, base / rel)
        added.append(str(rel))
    for rel, needle, add in NEEDLES:
        site = base / rel
        txt = site.read_text()
        assert txt.count(needle) == 1, f'{rel}: needle count {txt.count(needle)} != 1'
        site.write_text(txt.replace(needle, needle + add, 1))
    outdex = work / 'classes.dex'
    run(['java', '-cp', SMALI_CP, 'org.jf.smali.Main', 'assemble', '-j', '1', base, '-o', outdex])
    man = (bj / 'META-INF/MANIFEST.MF').read_bytes()
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for nm, data in (('META-INF/MANIFEST.MF', man), ('classes.dex', outdex.read_bytes())):
            zi = zipfile.ZipInfo(nm, (1980, 1, 1, 0, 0, 0))
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data)
    return sha(out), added


if __name__ == '__main__':
    b = sha(BASE)
    print('BASE u11i:', b)
    assert b.startswith(BASE_SHA), 'base jar is not U11i 5ae3dd29'
    s1, added = build(HERE / 'build/work1', OUT)
    s2, _ = build(HERE / 'build/work2', HERE / 'build/check.jar')
    print('CLASSES added:', ', '.join(added))
    print('OUTPUT u12 sha256:', s1)
    print('DETERMINISTIC:', 'YES' if s1 == s2 else f'NO {s1} {s2}')
    (HERE / 'build/check.jar').unlink()
    for w in ('work1', 'work2'):
        shutil.rmtree(HERE / 'build' / w)
    sys.exit(0 if s1 == s2 else 1)
