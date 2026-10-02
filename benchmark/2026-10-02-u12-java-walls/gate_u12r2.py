#!/usr/bin/env python3
"""U12 r2 gates against the unified state's jars (U10.1+T8+U11i, promoted 2026-10-02 17:52).

    gate_u12r2.py [--out gates/gate-u12r2.txt]

- deployed_class_diff --frozen: runtime u12r2 vs 5ae3dd29, stubs u12r2 vs 2f365a75 (the framework/ overlay the boards
  run); allow lists = exactly the classes this round adds.
- verify_identity: runtime vs 5ae3dd29 changes exactly the four needle methods; stubs vs 2f365a75 changes no deployed
  member; stubs vs U12 r1 stubs 3a12918a (net members) changes nothing either, so the android.net patch is carried
  unchanged.
- check_frozen.py.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths  # noqa: E402

WS = lab_paths.workspaces()
GEN = lab_paths.inputs() / 'generations'
V3 = GEN / 'u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/framework'
RUNTIME = HERE / 'build/oh-adapter-runtime-u12r2.jar'
STUBS = HERE / 'build/adapter-mainline-stubs-u12r2.jar'
STUBS_R1 = GEN / 'net-stubs-members-v1/on-2f365a75/adapter-mainline-stubs.jar'
VERIFY = REPO / 'benchmark/2026-10-02-android-net-stub-members/verify_identity.py'
RUNTIME_NEW = ['Ladapter/activity/OwnProviderLocal;', 'Ladapter/activity/ProviderAuthorityRefs;',
               'Ladapter/activity/TelephonyServiceNames;', 'Ladapter/activity/WlSettingsProvider;',
               'Ladapter/activity/WlSettingsStub;', 'Ladapter/activity/WlSettingsStub$$ExternalSyntheticLambda0;',
               'Ladapter/core/GcmDefaultNonce;', 'Ladapter/core/GcmDefaultNonce$1;', 'Ladapter/core/GcmDefaultNonce$Spi;',
               'Ladapter/core/GcmDefaultNonce$2;']
STUBS_NEW = [l.split('\t')[1].strip() for f in (REPO / 'benchmark/2026-10-02-android-net-stub-members/members.tsv',
                                                  HERE / 'stubs/members.tsv')
             for l in f.read_text().splitlines() if l.startswith('newclass\t')]
EXPECT = {
    'runtime 5ae3dd29 -> u12r2': {'Ladapter/activity/B7BindFixes;->apply(Landroid/content/pm/ApplicationInfo;)V',
                                  'Lcom/android/internal/os/AppSpawnXInit;->preInitSettingsCache()V',
                                  'Ladapter/activity/AppSchedulerBridge;->ensureBindApplication(Landroid/app/ActivityThread;Ljava/lang/String;[Ljava/lang/String;)V'},
    'stubs 2f365a75 -> u12r2': set(),
    'stubs 3a12918a (U12 r1) -> u12r2': set(),
}


def step(log, title, cmd):
    log.append(f'$ {title}')
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, cwd=REPO)
    out = (r.stdout + r.stderr).replace(str(WS), '$WORKSPACES').rstrip()
    log.append(out)
    log.append(f'rc={r.returncode}\n')
    return r.returncode, out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'gates/gate-u12r2.txt'))
    a = ap.parse_args()
    log, ok = [], {}
    diff = [sys.executable, REPO / 'scripts/lab/deployed_class_diff.py']
    rc, _ = step(log, 'runtime u12r2 vs unified 5ae3dd29', diff + [RUNTIME, '--deployed', V3 / 'oh-adapter-runtime.jar',
                                                                     '--frozen', '--allow-add', *RUNTIME_NEW])
    ok['class-diff runtime vs 5ae3dd29'] = rc == 0
    rc, _ = step(log, 'stubs u12r2 vs unified 2f365a75', diff + [STUBS, '--deployed', V3 / 'adapter-mainline-stubs.jar',
                                                                   '--frozen', '--allow-add', *STUBS_NEW])
    ok['class-diff stubs vs 2f365a75'] = rc == 0
    for name, before, after in (('runtime 5ae3dd29 -> u12r2', V3 / 'oh-adapter-runtime.jar', RUNTIME),
                                ('stubs 2f365a75 -> u12r2', V3 / 'adapter-mainline-stubs.jar', STUBS),
                                ('stubs 3a12918a (U12 r1) -> u12r2', STUBS_R1, STUBS)):
        rc, out = step(log, f'verify_identity {name}', [sys.executable, VERIFY, before, after])
        changed = set(re.findall(r'CHANGED (\S+)', out))
        good = changed == EXPECT[name] and 'class missing' not in out
        log.append(f'expected changed {sorted(EXPECT[name])}: {"YES" if good else "NO " + str(sorted(changed))}\n')
        ok['identity ' + name] = good
    rc, _ = step(log, 'check_frozen.py', [sys.executable, REPO / 'scripts/lab/check_frozen.py'])
    ok['check_frozen'] = rc == 0
    log.append('== summary')
    log += [f'{"PASS" if v else "FAIL"}  {k}' for k, v in ok.items()]
    Path(a.out).write_text('\n'.join(log) + '\n')
    print('\n'.join(log[-len(ok) - 1:]))
    return 0 if all(ok.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
