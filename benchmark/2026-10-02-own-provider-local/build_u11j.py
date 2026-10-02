#!/usr/bin/env python3
"""U11j JAR candidate = U11i (oh-adapter-runtime 5ae3dd29, the next round's JAR) + OwnProviderLocal (new file).

One smali needle, no existing class edited except the call site: B7BindFixes, right after
`ActivityManagerBindProxy.install()` (inside the same try block), adds `OwnProviderLocal.install()`. Same toolchain
as build_u11i.py (javac -source 8, d8.jar on openjdk@17, baksmali/smali 2.5.2 with jcommander-1.64, `smali -j 1`,
fixed zip timestamps). Built twice; the two jars must be byte-identical. Paths resolve from scripts/lab/lab_paths.py.
"""
import hashlib
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'scripts/lab'))
import lab_paths  # noqa: E402

WS = lab_paths.workspaces()
T = WS / 'westlake-harness-bms-deploy/bms/src/.work/b6-task45/inputs'
SMALI = lab_paths.tools() / 'smali-2.5.2.jar'
AJ = Path.home() / 'Library/Android/sdk/platforms/android-34/android.jar'
D8_JAVA = '/opt/homebrew/opt/openjdk@17/bin/java'
# U11i as persisted with the round's bundle (same bytes as 2026-10-01-u11-jar/build/oh-adapter-runtime-u11i.jar)
BASE = lab_paths.inputs() / 'generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/framework/oh-adapter-runtime.jar'
BASE_SHA = '5ae3dd29d45c2270'
SRC = HERE / 'src/OwnProviderLocal.java'
OUT = HERE / 'build/oh-adapter-runtime-u11j.jar'
BAK_CP = ':'.join(str(T / j) for j in ['baksmali-2.5.2.jar', 'dexlib2-2.5.2.jar', 'guava-27.1-android.jar',
                                       'jcommander-1.64.jar', 'util-2.5.2.jar'])
SMALI_CP = ':'.join([str(SMALI)] + [str(T / j) for j in ['dexlib2-2.5.2.jar', 'guava-27.1-android.jar', 'jcommander-1.64.jar',
                                                        'util-2.5.2.jar', 'antlr-runtime-3.5.2.jar',
                                                        'stringtemplate-3.2.1.jar']])
NEEDLE = '    invoke-static {}, Ladapter/activity/ActivityManagerBindProxy;->install()V\n'
ADD = '\n    invoke-static {}, Ladapter/activity/OwnProviderLocal;->install()V\n'


def pinned_javac():
    """The JDK the recorded build used (javac 21.0.6, mise temurin-21): $JAVA_HOME if >= 11, else mise's temurin-21.
    PATH is not trusted -- a bare PATH finds the system JDK 1.8, whose -target 8 output differs."""
    import os, re
    homes = [os.environ['JAVA_HOME'] + '/bin'] if os.environ.get('JAVA_HOME') else []
    homes += sorted(str(p) for p in (Path.home() / '.local/share/mise/installs/java').glob('temurin-21*/bin'))
    for h in homes:
        v = subprocess.run([h + '/javac', '-version'], capture_output=True, text=True)
        m = re.search(r'javac (\d+)', v.stdout + v.stderr)
        if m and int(m.group(1)) >= 11:
            return h + '/javac'
    raise SystemExit('need a JDK >= 11 (JAVA_HOME or mise temurin-21)')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(a):
    subprocess.run([str(x) for x in a], check=True)


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
    cc = work / 'classes'
    cc.mkdir()
    run([pinned_javac(), '-source', '8', '-target', '8', '-nowarn', '-cp', AJ, '-d', cc, SRC])
    dd = work / 'dex'
    dd.mkdir()
    run([D8_JAVA, '-cp', T / 'd8.jar', 'com.android.tools.r8.D8', '--min-api', '28', '--lib', AJ, '--output', dd,
         *sorted(cc.rglob('*.class'))])
    js = work / 'js'
    run(['java', '-cp', BAK_CP, 'org.jf.baksmali.Main', 'disassemble', dd / 'classes.dex', '-o', js])
    added = []
    for p in sorted(js.rglob('*.smali')):
        rel = p.relative_to(js)
        assert str(rel) not in before, f'{rel} already in the base jar'
        (base / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, base / rel)
        added.append(str(rel))
    site = base / 'adapter/activity/B7BindFixes.smali'
    txt = site.read_text()
    assert txt.count(NEEDLE) == 1, f'needle count {txt.count(NEEDLE)} != 1'
    site.write_text(txt.replace(NEEDLE, NEEDLE + ADD, 1))
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
    print('OUTPUT u11j sha256:', s1)
    print('DETERMINISTIC:', 'YES' if s1 == s2 else f'NO {s1} {s2}')
    (HERE / 'build/check.jar').unlink()
    for w in ('work1', 'work2'):
        shutil.rmtree(HERE / 'build' / w)
    sys.exit(0 if s1 == s2 else 1)
