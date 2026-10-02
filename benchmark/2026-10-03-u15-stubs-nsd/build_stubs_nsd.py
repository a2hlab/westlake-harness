#!/usr/bin/env python3
"""U15 stubs: U14 adapter-mainline-stubs 87cf65cc + android.net.nsd (NsdManager minimal + its 3 listener interfaces +
NsdServiceInfo), AOSP android-14.0.0_r1 packages/modules/Connectivity bd692130 framework-t/src/android/net/nsd.

    build_stubs_nsd.py

Recipe = ../2026-10-03-bt-le-scancallback/build_stubs_bt.py (which is the U12 recipe that built 615b8bbe): javac
--release 11 against the SDK android.jar + ./stubs/compile-only (hidden annotations, InetAddressUtils signatures; never
merged), d8 --release --min-api 29, baksmali/smali 2.5.2 -j 1, ../2026-10-02-android-net-stub-members/merge_smali.py
adds only the classes listed in ./stubs/members.tsv (every deployed member stays byte-identical), fixed zip time.
Built twice; must be byte-identical. Only BASE, OUT and this directory differ from the ScanCallback build.
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
if not NET.exists():
    NET = HERE.parents[1].parent / 'westlake-harness/benchmark/2026-10-02-android-net-stub-members'
sys.path.insert(0, str(HERE.parents[1] / 'scripts/lab'))
for _d in ('2026-10-02-u12-jar-plan', '2026-10-02-own-provider-local'):
    _p = HERE.parent / _d
    sys.path.insert(0, str(_p if _p.exists() else HERE.parents[1].parent / 'westlake-harness/benchmark' / _d))
import lab_paths  # noqa: E402
import build_u12 as r1  # noqa: E402

BASE = lab_paths.inputs() / 'generations/u14-stubs-bt-v1/adapter-mainline-stubs-u14-bt.jar'
BASE_SHA = '87cf65ccff4eda56183f98de2eb8e7740db6b7725e429c6799a570ae0b39e73a'
OUT = HERE / 'build/adapter-mainline-stubs-u15-nsd.jar'
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
    # Only deviation from the ScanCallback recipe: compile-only first, because the SDK android.jar carries
    # package-private android.annotation.NonNull/Nullable that would otherwise shadow the compile-only ones.
    run([javac, '--release', '11', '-nowarn', '-encoding', 'UTF-8', '-cp', f'{work / "compile-only"}:{r1.AJ}',
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
    assert sha(BASE) == BASE_SHA, 'base is not the U14 stubs 87cf65cc'
    s1, report = build(HERE / 'build/w1', OUT)
    s2, _ = build(HERE / 'build/w2', HERE / 'build/check.jar')
    (HERE / 'build/check.jar').unlink()
    (HERE / 'gates').mkdir(exist_ok=True)
    (HERE / 'gates/stubs-merge-report.json').write_text(report)
    for w in ('w1', 'w2'):
        shutil.rmtree(HERE / 'build' / w)
    print('STUBS base', BASE_SHA)
    print('STUBS u15-nsd (+android.net.nsd) sha256:', s1, 'DETERMINISTIC:', 'YES' if s1 == s2 else f'NO {s2}')
    sys.exit(0 if s1 == s2 else 1)
