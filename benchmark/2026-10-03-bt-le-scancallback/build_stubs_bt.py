#!/usr/bin/env python3
"""U14 stubs: U12/U13 adapter-mainline-stubs 615b8bbe + android.bluetooth.le.ScanCallback (AOSP 14 r1, verbatim).

    build_stubs_min.py

Adds android.bluetooth.le.ScanCallback (+ its nested annotation type ScanFailed), copied verbatim from AOSP
android-14.0.0_r1 packages/modules/Bluetooth cbb30d72 (framework/java/android/bluetooth/le/ScanCallback.java,
sha256 eae1a43c), from ./stubs (donor/, compile-only/ = the hidden android.annotation.IntDef, members.tsv), merged by
../2026-10-02-android-net-stub-members/merge_smali.py (adds only the listed members; every deployed member stays
byte-identical). Recipe and toolchain are those of ../2026-10-02-u12-jar-r2-bake/build_stubs_min.py (built U12 stubs
615b8bbe). Same deterministic toolchain as build_u12r2.py
(baksmali/smali 2.5.2 + jcommander-1.64, `smali -j 1`, fixed zip time); built twice, must be byte-identical.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
WALLS = HERE
NET = HERE.parent / '2026-10-02-android-net-stub-members'
sys.path.insert(0, str(HERE.parents[1] / 'scripts/lab'))
sys.path.insert(0, str(HERE.parent / '2026-10-02-u12-jar-plan'))
sys.path.insert(0, str(HERE.parent / '2026-10-02-own-provider-local'))
import lab_paths  # noqa: E402
import build_u12 as r1  # noqa: E402

BASE = lab_paths.inputs() / 'generations/u12-final-j0482c9b1-s615b8bbe-icu-media-zlib-v2/bundle/framework/adapter-mainline-stubs.jar'
BASE_SHA = '615b8bbecaa7b07fa27d40d25bd13eb6dfb33e6ec6bc7660bc2fc9aeaff1e610'
OUT = HERE / 'build/adapter-mainline-stubs-u14-bt.jar'
D8 = Path.home() / 'Library/Android/sdk/build-tools/37.0.0/d8'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(args, **kw):
    subprocess.run([str(a) for a in args], check=True, **kw)


def build(work, out):
    if work.exists():
        shutil.rmtree(work)
    for d in ('classes', 'compile-only', 'dex', 'base'):
        (work / d).mkdir(parents=True)
    javac = r1.pinned_javac()
    run([javac, '--release', '11', '-nowarn', '-encoding', 'UTF-8', '-cp', r1.AJ, '-d', work / 'compile-only',
         *sorted((WALLS / 'stubs/compile-only').rglob('*.java'))])
    run([javac, '--release', '11', '-nowarn', '-encoding', 'UTF-8', '-cp', f'{r1.AJ}:{work / "compile-only"}',
         '-d', work / 'classes', *sorted((WALLS / 'stubs/donor').rglob('*.java'))])
    env = dict(os.environ, PATH=str(Path(javac).parent) + os.pathsep + os.environ.get('PATH', ''))
    run([D8, '--release', '--min-api', '29', '--lib', r1.AJ, '--classpath', work / 'compile-only',
         '--output', work / 'dex', *sorted((work / 'classes').rglob('*.class'))], env=env)
    run(['java', '-cp', r1.BAK_CP, 'org.jf.baksmali.Main', 'disassemble', work / 'dex/classes.dex', '-o',
         work / 'donor_smali'])
    with zipfile.ZipFile(BASE) as z:
        (work / 'base/classes.dex').write_bytes(z.read('classes.dex'))
        entries = [(i, z.read(i.filename)) for i in z.infolist()]
    run(['java', '-cp', r1.BAK_CP, 'org.jf.baksmali.Main', 'disassemble', work / 'base/classes.dex', '-o',
         work / 'base/smali'])
    run([sys.executable, NET / 'merge_smali.py', work / 'base/smali', work / 'donor_smali', WALLS / 'stubs/members.tsv',
         '--report', work / 'merge-report.json'])
    run(['java', '-cp', r1.SMALI_CP, 'org.jf.smali.Main', 'assemble', '-a', '29', '-j', '1', work / 'base/smali',
         '-o', work / 'merged.dex'])
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    with zipfile.ZipFile(out, 'w', zipfile.ZIP_DEFLATED) as z:
        for info, data in entries:
            if info.filename == 'classes.dex':
                data = (work / 'merged.dex').read_bytes()
            zi = zipfile.ZipInfo(info.filename, (1980, 1, 1, 0, 0, 0))
            zi.external_attr = 0o644 << 16
            z.writestr(zi, data)
    return sha(out), (work / 'merge-report.json').read_text()


if __name__ == '__main__':
    assert sha(BASE) == BASE_SHA, 'base is not the U12/U13 stubs 615b8bbe'
    s1, report = build(HERE / 'build/w1', OUT)
    s2, _ = build(HERE / 'build/w2', HERE / 'build/check.jar')
    (HERE / 'build/check.jar').unlink()
    (HERE / 'gates').mkdir(exist_ok=True)
    (HERE / 'gates/stubs-merge-report.json').write_text(report)
    for w in ('w1', 'w2'):
        shutil.rmtree(HERE / 'build' / w)
    print('STUBS base', BASE_SHA)
    print('STUBS u14-bt (+ScanCallback) sha256:', s1, 'DETERMINISTIC:', 'YES' if s1 == s2 else f'NO {s2}')
    sys.exit(0 if s1 == s2 else 1)
