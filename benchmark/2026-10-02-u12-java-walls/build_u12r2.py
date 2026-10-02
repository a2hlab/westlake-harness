#!/usr/bin/env python3
"""U12 r2: the round's single JAR version, U12 (2026-10-02-u12-jar-plan) plus the Java-layer walls of this directory.

    build_u12r2.py [runtime|stubs|all]

runtime (oh-adapter-runtime.jar): U11i 5ae3dd29 (the unified state's runtime) + OwnProviderLocal + WlSettingsProvider
  + WlSettingsStub (U12 r1, unchanged) + ProviderAuthorityRefs + TelephonyServiceNames + GcmDefaultNonce. Built with
  build_u12.py's toolchain and needles plus two needles:
    B7BindFixes, after SystemServiceFetcherStubs.install() (same try block): TelephonyServiceNames.install(),
      GcmDefaultNonce.install()
    AppSchedulerBridge.ensureBindApplication, after B8BindExtras.afterProviders(bindData): ProviderAuthorityRefs.resolve
  Built twice; must be byte-identical.
stubs (adapter-mainline-stubs.jar, boot class path): the unified state's 2f365a75 + the android.net members of
  2026-10-02-android-net-stub-members (donor/, members.tsv) + stubs/donor + stubs/members.tsv here
  (TelephonyFrameworkInitializer.getTelephonyServiceManager, com.android.internal.util.Predicate), merged by that
  directory's merge_smali.py (adds only listed members; every deployed member stays byte-identical). Deterministic:
  baksmali/smali 2.5.2 with jcommander-1.64 and `smali -j 1` (the U11i classpath), fixed zip entry time, built twice.
  A boot-class-path jar: deploying it needs the FZ-005 image rebake and T8's four gates.
"""
import hashlib
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
sys.path.insert(0, str(HERE.parent / '2026-10-02-u12-jar-plan'))
sys.path.insert(0, str(HERE.parent / '2026-10-02-own-provider-local'))
import lab_paths  # noqa: E402
import build_u12 as r1  # noqa: E402

NET = HERE.parent / '2026-10-02-android-net-stub-members'
STUBS_BASE = lab_paths.inputs() / 'generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/framework/adapter-mainline-stubs.jar'
STUBS_BASE_SHA = '2f365a75581b'
RUNTIME_OUT = HERE / 'build/oh-adapter-runtime-u12r2.jar'
STUBS_OUT = HERE / 'build/adapter-mainline-stubs-u12r2.jar'
NEW_SRCS = [HERE / 'src-runtime/adapter/activity/ProviderAuthorityRefs.java',
            HERE / 'src-runtime/adapter/activity/TelephonyServiceNames.java',
            HERE / 'src-runtime/adapter/core/GcmDefaultNonce.java']
NEW_NEEDLES = [
    ('adapter/activity/B7BindFixes.smali',
     '    invoke-static {}, Ladapter/activity/SystemServiceFetcherStubs;->install()V\n',
     '\n    invoke-static {}, Ladapter/activity/TelephonyServiceNames;->install()V\n'
     '\n    invoke-static {}, Ladapter/core/GcmDefaultNonce;->install()V\n'),
    ('adapter/activity/AppSchedulerBridge.smali',
     '    invoke-static {v13}, Ladapter/activity/B8BindExtras;->afterProviders(Ljava/lang/Object;)V\n',
     '\n    invoke-static {v13}, Ladapter/activity/ProviderAuthorityRefs;->resolve(Ljava/lang/Object;)V\n'),
]
SDK = Path.home() / 'Library/Android/sdk'
D8 = SDK / 'build-tools/37.0.0/d8'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def run(args, **kw):
    subprocess.run([str(a) for a in args], check=True, **kw)


def build_runtime():
    merged = HERE / 'build/compile-only-merged'
    if merged.exists():
        shutil.rmtree(merged)
    shutil.copytree(r1.COMPILE_ONLY, merged)
    shutil.copytree(HERE / 'compile-only-runtime', merged, dirs_exist_ok=True)
    r1.COMPILE_ONLY = merged
    r1.SRCS = list(r1.SRCS) + NEW_SRCS
    r1.NEEDLES = list(r1.NEEDLES) + NEW_NEEDLES
    s1, added = r1.build(HERE / 'build/rt1', RUNTIME_OUT)
    s2, _ = r1.build(HERE / 'build/rt2', HERE / 'build/rt-check.jar')
    (HERE / 'build/rt-check.jar').unlink()
    for w in ('rt1', 'rt2', 'compile-only-merged'):
        shutil.rmtree(HERE / 'build' / w)
    print('RUNTIME classes added:', ', '.join(added))
    print('RUNTIME u12r2 sha256:', s1, 'DETERMINISTIC:', 'YES' if s1 == s2 else f'NO {s2}')
    return s1 == s2


def build_stubs_once(work, out):
    if work.exists():
        shutil.rmtree(work)
    for d in ('classes', 'compile-only', 'dex', 'base'):
        (work / d).mkdir(parents=True)
    javac = r1.pinned_javac()
    run([javac, '--release', '11', '-nowarn', '-encoding', 'UTF-8', '-cp', r1.AJ, '-d', work / 'compile-only',
         *sorted((HERE / 'stubs/compile-only').rglob('*.java'))])
    donors = sorted((NET / 'donor').rglob('*.java')) + sorted((HERE / 'stubs/donor').rglob('*.java'))
    run([javac, '--release', '11', '-nowarn', '-encoding', 'UTF-8', '-cp', f'{r1.AJ}:{work / "compile-only"}',
         '-d', work / 'classes', *donors])
    env = dict(os.environ, PATH=str(Path(javac).parent) + os.pathsep + os.environ.get('PATH', ''))
    run([D8, '--release', '--min-api', '29', '--lib', r1.AJ, '--classpath', work / 'compile-only',
         '--output', work / 'dex', *sorted((work / 'classes').rglob('*.class'))], env=env)
    run(['java', '-cp', r1.BAK_CP, 'org.jf.baksmali.Main', 'disassemble', work / 'dex/classes.dex', '-o',
         work / 'donor_smali'])
    with zipfile.ZipFile(STUBS_BASE) as z:
        (work / 'base/classes.dex').write_bytes(z.read('classes.dex'))
        entries = [(i, z.read(i.filename)) for i in z.infolist()]
    run(['java', '-cp', r1.BAK_CP, 'org.jf.baksmali.Main', 'disassemble', work / 'base/classes.dex', '-o',
         work / 'base/smali'])
    members = work / 'members.tsv'
    members.write_text((NET / 'members.tsv').read_text() + (HERE / 'stubs/members.tsv').read_text())
    run([sys.executable, NET / 'merge_smali.py', work / 'base/smali', work / 'donor_smali', members,
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


def build_stubs():
    b = sha(STUBS_BASE)
    assert b.startswith(STUBS_BASE_SHA), f'stubs base is not 2f365a75: {b}'
    s1, report = build_stubs_once(HERE / 'build/st1', STUBS_OUT)
    s2, _ = build_stubs_once(HERE / 'build/st2', HERE / 'build/st-check.jar')
    (HERE / 'build/st-check.jar').unlink()
    (HERE / 'gates/stubs-merge-report.json').write_text(report)
    for w in ('st1', 'st2'):
        shutil.rmtree(HERE / 'build' / w)
    print('STUBS base', b)
    print('STUBS u12r2 sha256:', s1, 'DETERMINISTIC:', 'YES' if s1 == s2 else f'NO {s2}')
    return s1 == s2


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    ok = True
    if what in ('runtime', 'all'):
        ok &= build_runtime()
    if what in ('stubs', 'all'):
        ok &= build_stubs()
    sys.exit(0 if ok else 1)
