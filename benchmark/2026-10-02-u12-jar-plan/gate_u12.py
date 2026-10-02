#!/usr/bin/env python3
"""U12 gates: each of the round's two changed jars against BOTH board bases, plus member identity and check_frozen.

    gate_u12.py [--out gates/gate-u12.txt]

Bases (the framework/ overlay the boards actually run, not the native/payload underlay):
  promoted   = the T8 v3 package  u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/framework/   (runtime 5ae3dd29, stubs 2f365a75)
  unpromoted = U9                 westlake-generation-u9-j10g-238ffc14/framework/           (runtime 238ffc14, stubs f3bcc9d7)
Allow lists: this round's own new classes only on the promoted base; on U9 additionally the outer-approved T8 policy
(benchmark/2026-10-02-u10-1-t8-rerun/approved-static-policy-current.json), i.e. exactly the promotion delta U12 inherits.
Every step must exit 0, except verify_identity, which must name exactly the expected changed methods.
"""
import argparse
import json
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
U9 = WS / 'westlake-generation-u9-j10g-238ffc14/framework'
RUNTIME = HERE / 'build/oh-adapter-runtime-u12.jar'
STUBS = GEN / 'net-stubs-members-v1/on-2f365a75/adapter-mainline-stubs.jar'
U11J = GEN / 'u11j-own-provider-local-v1/oh-adapter-runtime-u11j.jar'
POLICY = REPO / 'benchmark/2026-10-02-u10-1-t8-rerun/approved-static-policy-current.json'
NET = REPO / 'benchmark/2026-10-02-android-net-stub-members'
RUNTIME_NEW = ['Ladapter/activity/OwnProviderLocal;', 'Ladapter/activity/WlSettingsProvider;',
               'Ladapter/activity/WlSettingsStub;', 'Ladapter/activity/WlSettingsStub$$ExternalSyntheticLambda0;']
EXPECT_CHANGED = {
    'U11i->U12': {'Ladapter/activity/B7BindFixes;->apply(Landroid/content/pm/ApplicationInfo;)V',
                  'Lcom/android/internal/os/AppSpawnXInit;->preInitSettingsCache()V'},
    'U11j->U12': {'Lcom/android/internal/os/AppSpawnXInit;->preInitSettingsCache()V'},
}


def stubs_new():
    return [l.split('\t')[1].strip() for l in (NET / 'members.tsv').read_text().splitlines()
            if l.startswith('newclass\t')]


def policy(jar):
    return json.loads(POLICY.read_text())['jars'][f'/system/android/framework/{jar}']


def step(log, title, cmd):
    log.append(f'$ {title}')
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, cwd=REPO)
    out = (r.stdout + r.stderr).replace(str(WS), '$WORKSPACES').rstrip()
    log.append(out)
    log.append(f'rc={r.returncode}\n')
    return r.returncode, out


def diff(log, title, cand, deployed, add=(), drop=(), reshape=()):
    cmd = [sys.executable, REPO / 'scripts/lab/deployed_class_diff.py', cand, '--deployed', deployed, '--frozen']
    for flag, xs in (('--allow-add', add), ('--allow-drop', drop), ('--allow-reshape', reshape)):
        if xs:
            cmd += [flag, *xs]
    rc, _ = step(log, title, cmd)
    return rc == 0


def identity(log, name, before, after):
    rc, out = step(log, f'verify_identity.py {name} (expected changed: {sorted(EXPECT_CHANGED[name])})',
                   [sys.executable, NET / 'verify_identity.py', before, after])
    changed = set(re.findall(r'CHANGED (\S+)', out))
    ok = changed == EXPECT_CHANGED[name]
    log.append(f'expected-changed match: {"YES" if ok else "NO " + str(sorted(changed))}\n')
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'gates/gate-u12.txt'))
    a = ap.parse_args()
    log, ok = [], {}
    rp, sp = policy('oh-adapter-runtime.jar'), policy('adapter-mainline-stubs.jar')
    ok['runtime vs promoted 5ae3dd29'] = diff(log, 'runtime U12 vs promoted base (v3) 5ae3dd29', RUNTIME,
                                              V3 / 'oh-adapter-runtime.jar', add=RUNTIME_NEW)
    ok['runtime vs U9 238ffc14'] = diff(log, 'runtime U12 vs unpromoted base (U9) 238ffc14; + approved T8 policy',
                                        RUNTIME, U9 / 'oh-adapter-runtime.jar', add=rp['allow_add'] + RUNTIME_NEW,
                                        drop=rp.get('allow_drop', []), reshape=rp.get('allow_reshape', []))
    ok['stubs vs promoted 2f365a75'] = diff(log, 'stubs U12 (net-stubs-members-v1 on-2f365a75) vs promoted base 2f365a75',
                                            STUBS, V3 / 'adapter-mainline-stubs.jar', add=stubs_new())
    ok['stubs vs U9 f3bcc9d7'] = diff(log, 'stubs U12 vs unpromoted base (U9) f3bcc9d7; + approved T8 policy', STUBS,
                                      U9 / 'adapter-mainline-stubs.jar', add=sp['allow_add'] + stubs_new(),
                                      drop=sp.get('allow_drop', []), reshape=sp.get('allow_reshape', []))
    ok['identity U11i->U12'] = identity(log, 'U11i->U12', V3 / 'oh-adapter-runtime.jar', RUNTIME)
    ok['identity U11j->U12'] = identity(log, 'U11j->U12', U11J, RUNTIME)
    rc, _ = step(log, 'check_frozen.py', [sys.executable, REPO / 'scripts/lab/check_frozen.py'])
    ok['check_frozen'] = rc == 0
    log.append('== summary')
    log += [f'{"PASS" if v else "FAIL"}  {k}' for k, v in ok.items()]
    Path(a.out).write_text('\n'.join(log) + '\n')
    print('\n'.join(log[-len(ok) - 1:]))
    return 0 if all(ok.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
