#!/usr/bin/env python3
"""Offline only: pin G05 fresh member lists and generate a disabled G06 board_run plan."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
from recovery_hook import APK_SHA, BATCH, SERIAL, require, save, sha, packages, power, focus

D = Path(__file__).resolve().parent
ROOT = D.parents[2]


def member_map(path):
    result = {}
    for line in path.read_text().splitlines():
        m = re.fullmatch(r'([0-9a-f]{64})\s+(/\S+)', line)
        require(m is not None and m[2] not in result, 'bad member line')
        result[m[2]] = m[1]
    require(bool(result), 'empty member set')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--g05-root', type=Path, required=True)
    p.add_argument('--repo', type=Path, default=ROOT)
    p.add_argument('--window', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--lane', default='cc-video')
    a = p.parse_args()
    require(not a.out.exists() and not a.window.exists(), 'fresh output/window required')
    repo = a.repo.resolve(); raw = a.g05_root / 'raw'
    evidence = []
    for tag in ['r01-boot-before', 'r02-fresh-fp', 'r03-launch-config', 'r04-bm-dump-full',
                'r05-wms-dump', 'r06-power-dump', 'r07-install-dirs-before', 'r08-boot-after']:
        require((raw / (tag + '.rc')).read_text().strip() == '0', tag + ' process rc')
        for suffix in ['argv.json', 'stdout', 'stderr', 'rc']:
            f = raw / (tag + '.' + suffix)
            evidence.append({'alias': 'G05_PRIVATE/' + str(f.relative_to(a.g05_root)), 'sha256': sha(f), 'bytes': f.stat().st_size})
    before = (raw / 'r01-boot-before.stdout').read_text().splitlines()[0]
    after = (raw / 'r08-boot-after.stdout').read_text().splitlines()[0]
    require(before == after and re.fullmatch(r'[0-9a-f-]{36}', before), 'boot mismatch')
    require('com.miHoYo.Yuanshen' not in packages(0, (raw/'r04-bm-dump-full.stdout').read_text()), 'target already installed')
    require(power((raw/'r06-power-dump.stdout').read_text()) == {'state':'SLEEP','timeout':30000,'override':10000}, 'unexpected power')
    require(focus((raw/'r05-wms-dump.stdout').read_text()).startswith('SCBScreenLock'), 'unexpected foreground')
    fingerprints = {}
    for kind, file, n, expected in [('runtime','runtime-fingerprint.txt',124,'fd464714645b'),
                                    ('boot','boot-image-fingerprint.txt',36,'ee927db88a67')]:
        f = a.g05_root/'fresh-fp'/file
        members = member_map(f)
        actual = hashlib.sha256('\n'.join(sorted(f.read_text().splitlines())).encode()).hexdigest()[:12]
        require(len(members) == n and actual == expected, 'fresh underlying member mismatch')
        fingerprints[kind] = members
        evidence.append({'alias':'G05_PRIVATE/fresh-fp/'+file,'sha256':sha(f),'bytes':f.stat().st_size})
    for i in [1, 2]:
        for suffix in ['rc','remote_rc']:
            require((a.g05_root/'fresh-fp'/f'shim-{i:02d}.{suffix}').read_text().strip() == '0', 'fresh fingerprint rc')
    meta = a.g05_root/'input-root/genshin/app-input.json'
    data = json.loads(meta.read_text()); apk = Path(data['apk'])
    require(data['apk_sha256'] == APK_SHA and apk.stat().st_size == 513290344 and sha(apk) == APK_SHA, 'APK changed')
    a.out.mkdir(parents=True)
    (a.out/'input-root/genshin').mkdir(parents=True)
    shutil.copyfile(meta, a.out/'input-root/genshin/app-input.json')
    (a.out/'genshin.keys').write_text('genshin\n')
    manifest = {'schema':1, 'baseline':'G06-current-5ea-no-runtime-change', 'order':['genshin'], 'apps':[
        {'key':'genshin','package':'com.miHoYo.Yuanshen','apk_sha256':APK_SHA,
         'launch_activity':'com.miHoYo.GetMobileInfo.MainActivity','phase':'controls'}]}
    save(a.out/'manifest.json', manifest)
    source_paths = [BATCH, 'scripts/lab/board_run.py', 'scripts/lab/board_note.sh',
                    'scripts/lab/activation_smoke.py', 'scripts/lab/installation_chain.py',
                    'benchmark/2026-09-28-bms-route-deploy/batch/prepare_sandbox.sh']
    pins = {x:sha(repo/x) for x in source_paths}
    cfg = {'schema':1, 'approved_by':None, 'serial':SERIAL,'lane':a.lane,'repo':str(repo),
           'window':str(a.window.resolve()),'expected_boot':before, 'input_sha256':sha(meta),
           'apk_sha256':APK_SHA, 'source_pins':pins,'fingerprints':fingerprints,
           'retention_policy':'retain this-window verified package and data; stop exact target; no uninstall'}
    cfg['hook_path'] = str(D/'recovery_hook.py')
    cfg['hook_sha256'] = sha(D/'recovery_hook.py')
    save(a.out/'hook-config.unsigned.json', cfg)
    smoke = {'expect':{'runtime_fp':'fd464714645b','boot_fp':'ee927db88a67'}, 'fixes':[],
             'groups':[{'manifest':str(repo/'knowledge/smoke/controls-apps.json'),'keys':['zigzag'],
                        'mode':'launch-only','controls':True,
                        'input_root':'$WORKSPACES/westlake-b90-controls-inputs'}]}
    save(a.out/'smoke.json',smoke)
    hook = str(D/'recovery_hook.py')
    cfgpath = str(a.out.resolve()/'hook-config.unsigned.json')
    plan = {'serial':SERIAL,'lane':a.lane,'entry':'91','why':'G06 exact official Genshin first launch',
            'board':str(repo/'.octos/boards/app-lighting.md'),'out':str(a.window.resolve()),
            'execution_enabled':False,'stop_new_tests_by_minute':20,
            'window_budget_note':'1800s outer wall-clock supervision; board_run has no hard global window timer',
            'smoke_spec':str(a.out.resolve()/'smoke.json'),
            'after_lock':[sys.executable,hook,'before','--config',cfgpath,'--execute'],
            'before_unlock':[sys.executable,hook,'restore','--config',cfgpath,'--execute'],
            'offline_precheck':{'hypothesis':'exact package may reach first frame or expose first runtime blocker without runtime changes',
                'evidence':[str(a.out.resolve()/'input-evidence.json')],
                'expect':{'confirm':'actual BMS install readback and reviewed t5/t20 image',
                          'refute':'actual install/start error or no first frame; no static root-cause substitution'},
                'result':'not-falsified'},
            'shards':[{'name':'shards','wait_seconds':60,'shots':[5,20,60],
                       'manifest':str(a.out.resolve()/'manifest.json'),
                       'input_root':str(a.out.resolve()/'input-root'),'keys_file':str(a.out.resolve()/'genshin.keys')}]}
    plan['requires_g07'] = 'outer must verify current board_run consumes wait_seconds/shots; old board_run ignores these fields'
    save(a.out/'board-run.disabled.json',plan)
    save(a.out/'input-evidence.json',{'raw':evidence,'apk_sha256':APK_SHA,'metadata_sha256':sha(meta),
                                   'fingerprint_members':{k:len(v) for k,v in fingerprints.items()}})
    print(json.dumps({'status':'OFFLINE_DISABLED_PLAN_READY','out':str(a.out),
                      'runtime':'NOT_TESTED','approval':None,'metadata_sha256':sha(meta)}))


if __name__ == '__main__':
    main()
