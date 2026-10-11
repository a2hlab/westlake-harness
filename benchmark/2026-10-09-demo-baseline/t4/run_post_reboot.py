#!/usr/bin/env python3
"""Compile/drive all 128 installed demo apps in bounded, exclusive selected-board windows.
Default is offline preparation. --execute needs explicit outer authorization;
--detach detaches the entire multi-window driver, not just its first window.
No reboot, installation, runtime deployment or repair is performed here.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid
import shlex

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
REPO = BASE.parents[1]
WS = Path(os.environ.get('WORKSPACES', REPO.parent))
MASTER = WS / 'westlake-harness'
SERIAL = '61b0657200000000000000000324012c'
ALLOWED_SERIALS = frozenset({'61b0657200000000000000000324012c', '5cd1e3dd00000000000000000923012c', '5ea34a4500000000000000001123012c'})

def validate_serial(serial):
    if serial not in ALLOWED_SERIALS:
        raise ValueError('serial outside demo whitelist: ' + str(serial))
    return serial



def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


prep = module('demo_prepare_t3', BASE / 'prepare_t3.py')
regress = module('demo_regress', HERE / 'regress_vs_signoff.py')


def read(p):
    return json.loads(Path(p).read_text())


def save(p, value):
    Path(p).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def portable(p):
    return str(Path(p).resolve()).replace(str(WS), '$WORKSPACES')


def expand(p):
    return Path(os.path.expandvars(str(p).replace('$WORKSPACES', str(WS))))


def pin(p):
    return {'path': portable(p), 'sha256': regress.sha(p)}


def prepare(manifest, tiers, install_index, out, boot_before, smoke, count=18, serial=SERIAL):
    validate_serial(serial)
    if out.exists():
        raise ValueError('fresh round directory required')
    if not __import__('re').fullmatch(r'[0-9a-f-]{36}', boot_before):
        raise ValueError('actual pre-reboot boot ID required; this driver never reboots')
    doc, shots, index = read(manifest), read(tiers), read(install_index)
    entries, _, windows = prep.plans(doc, portable(out), portable(smoke), count=count)
    # t5 subset (user 2026-10-11, Plan-2): run exactly the manifest's installable keys (<=128), not a hardcoded 128.
    selected = [a for a in doc['apps'] if a.get('install') is not False]
    if len(entries) != len(selected):
        raise ValueError('selected packages must match the manifest (install!=false)')
    bykey = {r['key']: r for r in shots['apps']}
    if not {a['key'] for a, _ in entries} <= set(bykey):
        raise ValueError('tier key set must cover the run keys')
    for app, _ in entries:
        row = bykey[app['key']]
        if any(row[k] != app[k] for k in ('package', 'apk_sha256')) or row['screenshot_seconds'] not in (10, 20):
            raise ValueError('tier identity/delay mismatch')
        if index.get(app['key'], {}).get('success') is not True or index[app['key']]['apk_sha256'] != app['apk_sha256']:
            raise ValueError('t3 install receipt not verified: ' + app['key'])
    out.mkdir(parents=True)
    # Use t3's exact canonical app preparation; installation was already completed before reboot.
    save(out / 'batch-apps.json', {'apps': [a for a, _ in entries]})
    save(out / 'install-index.json', json.loads(json.dumps(index).replace(str(WS), '$WORKSPACES')))
    save(out / 'shot-tiers.json', shots)
    configuration = {'schema': 'demo-post-reboot-executor/v1', 'serial': serial,
                     'execution_enabled': False, 'boot_before_reboot': boot_before,
                     'base': 'signed U13', 'apps': len(entries), 'windows': [],
                     'bindings': {name: pin(p) for name, p in {'manifest': manifest, 'tiers': tiers,
                           'install_index': install_index, 'smoke': smoke,
                           'prepare_t3': BASE / 'prepare_t3.py', 'driver': Path(__file__),
                           'identity_hook': HERE / 'round_identity.py',
                           't3_identity': BASE / 't3/verify_identity.py',
                           'comparator': HERE / 'regress_vs_signoff.py',
                           'facts': MASTER / 'scripts/lab/run_facts.py',
                           'toutiao_hook': HERE / 'foreground_toutiao.py',
                           'adapter': BASE / 't3/batch_adapter.py', 'runner': BASE / 't3/demo_board_run.py',
                           'master_runner': MASTER / 'scripts/lab/board_run.py',
                           'master_batch': MASTER / 'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'}.items()},
                     'special_slots': {'toutiao': {'enabled': False, 'launch': 'foreground-desktop-click',
                           'host_package': 'org.westlake.imehost', 'identity_files': {},
                           'note': 'Explicit reviewed installed Route B identity required; no provisioning.'},
                           'boatattack': {'enabled': False, 'plan': None, 'plan_sha256': None,
                           'note': 'Reserved separate approved board_run plan; no overlay installation here.'}}}
    pins = {}
    for candidate in (BASE / 't3/plans-v2/capture-02-resume/plan.json', BASE / 't3/plans-v2/capture-05-icon-retry/plan.json'):
        if candidate.is_file():
            pins.update(read(candidate).get('demo_ability_pins', {}))
    for folder, plan, group in windows:
        d = out / folder
        d.mkdir()
        for app, _ in group:
            (d / (app['key'] + '.keys')).write_text(app['key'] + '\n')
        plan.update(serial=serial, why='Demo t4 post-reboot installed-only full regression; window ' + folder,
                    demo_mode='launch', demo_shot_tiers=portable(out / 'shot-tiers.json'),
                    demo_shot_tiers_sha256=regress.sha(out / 'shot-tiers.json'),
                    demo_install_index=portable(out / 'install-index.json'),
                    demo_ability_pins={a['key']: pins[a['key']] for a, _ in group if a['key'] in pins},
                    pending_before_execution=[],
                    after_lock=[sys.executable, portable(HERE / 'round_identity.py'), '--round', portable(out),
                                '--out', portable(d / 'before-identity')],
                    before_unlock=[sys.executable, portable(HERE / 'round_identity.py'), '--round', portable(out),
                                   '--out', portable(d / 'after-identity')])
        plan['offline_precheck']['expect'] = {
            'confirm': 'All 128 installed pinned keys produce t10/t20 snapshots on the same post-reboot U13 boot; outer signs UI.',
            'refute': 'Identity/boot/infra drift or missing record stops the round; no manual runtime repair.'}
        save(d / 'plan.json', plan)
        configuration['windows'].append(portable(d / 'plan.json'))
    # Bind generated inputs too; enabling is deliberately the only permitted plan mutation below.
    for p in [out / 'batch-apps.json', out / 'shot-tiers.json', out / 'install-index.json']:
        configuration['bindings'][p.name] = pin(p)
    configuration['window_bindings'] = [pin(expand(p)) for p in configuration['windows']]
    save(out / 'round.json', configuration)
    print(json.dumps({'state': 'PREPARED_DISABLED', 'apps': 128, 'windows': len(windows),
                     'shot_tiers': {str(t): sum(r['screenshot_seconds'] == t for r in bykey.values()) for t in (10, 20)},
                     'device_access': False}))
    return configuration


def collect(out):
    found = {}
    for window in read(out / 'round.json')['windows']:
        plan = read(expand(window))
        root = expand(window).parent / 'runner'
        for shard in plan['shards']:
            rows = regress.records(root / shard['name'])
            if set(found) & set(rows):
                raise ValueError('duplicate canonical round key')
            found.update(rows)
    view = out / 'final'
    if view.exists():
        raise ValueError('fresh aggregate view required')
    base = view / validate_serial(read(out / 'round.json')['serial'])
    base.mkdir(parents=True)
    for key, p in found.items():
        (base / key).symlink_to(p.parent.resolve(), target_is_directory=True)
    for name in ('runtime-fingerprint.txt', 'boot-image-fingerprint.txt', 'plan.json'):
        values = [p.parent.parent / name for p in found.values()]
        if values and all(p.is_file() for p in values) and len({p.read_bytes() for p in values}) == 1:
            (base / name).write_bytes(values[0].read_bytes())
    facts = subprocess.check_output([sys.executable, str(MASTER / 'scripts/lab/run_facts.py'), str(view)], text=True)
    (out / 'facts.txt').write_text(facts)
    print(facts, end='')
    return found


def resolve_inputs(out):
    config = read(out / 'round.json')
    apps = read(out / 'batch-apps.json')['apps']
    roots = sorted({a['input_root'] for a in apps})
    for i, root in enumerate(roots):
        keys = ','.join(a['key'] for a in apps if a['input_root'] == root)
        cmd = ['python3', str(MASTER / 'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'),
               '--resolve-inputs', '--manifest', str(out / 'batch-apps.json'), '--input-root', str(expand(root)),
               '--keys', keys, '--out', str(out / ('resolved-' + str(i)))]
        # Resolution checks files only; the production VM path is checked before taking any lock.
        with (out / ('resolve-' + str(i) + '.log')).open('w') as log:
            rc = subprocess.run(['orb', '-m', 'a2hlab', 'env', 'WORKSPACES=' + str(WS),
                                 'MAC_HOME=' + str(Path.home()), *cmd], stdout=log, stderr=subprocess.STDOUT).returncode
        if rc:
            raise RuntimeError('pre-lock input resolution failed')


def validate_special_slots(config):
    slots = config['special_slots']
    tou = slots['toutiao']
    if tou.get('enabled'):
        if config['serial'] != SERIAL:
            raise ValueError('Toutiao foreground slot is currently authorized for 61b only')
        if tou.get('host_package') != 'org.westlake.imehost' or not tou.get('identity_files'):
            raise ValueError('Toutiao requires reviewed exact host and nonempty installed artifact pins')
        import re
        for target, digest in tou['identity_files'].items():
            if not target.startswith(('/data/', '/system/')) or not re.fullmatch('[0-9a-f]{64}', digest):
                raise ValueError('invalid Toutiao installed artifact binding')
    boat = slots['boatattack']
    if boat.get('enabled'):
        if not boat.get('plan') or not boat.get('plan_sha256'):
            raise ValueError('BoatAttack slot has no approved bound plan')
        path = expand(boat['plan'])
        plan = read(path)
        if regress.sha(path) != boat['plan_sha256'] or plan.get('serial') != validate_serial(config['serial']) or plan.get('execution_enabled') is not True:
            raise ValueError('BoatAttack plan binding/61b authorization mismatch')
        if not plan.get('before_unlock') or not 0 < plan.get('window_limit_minutes', 0) <= 30:
            raise ValueError('BoatAttack requires final hook and bounded dedicated window')


def execute(out, authorization):
    config = read(out / 'round.json')
    serial = validate_serial(config['serial'])
    if not authorization.strip():
        raise ValueError('explicit outer authorization reference required')
    validate_special_slots(config)
    for value in config['bindings'].values():
        if regress.sha(expand(value['path'])) != value['sha256']:
            raise ValueError('pinned driver/input changed before dispatch')
    for value in config['window_bindings']:
        if regress.sha(expand(value['path'])) != value['sha256']:
            raise ValueError('prepared window plan drift')
    resolve_inputs(out)
    for path in config['windows']:
        plan_path = expand(path)
        plan = read(plan_path)
        # The round is detached once; each board_run synchronously finishes/unlocks before the next.
        subprocess.run(['orb', '-m', 'a2hlab', 'true'], check=True, timeout=20)
        subprocess.run(['hdc', 'list', 'targets'], check=True, timeout=20)
        subprocess.run([sys.executable, str(HERE / 'round_identity.py'), '--round', str(out),
                        '--out', str(plan_path.parent / 'pre-lock-identity')], check=True)
        plan['execution_enabled'] = True
        save(plan_path, plan)
        note = WS / 'westlake-inputs/tools/board_note.sh'
        subprocess.run([str(note), 'progress', str(MASTER / '.octos/boards/app-lighting.md'), '91', 'cx-t0',
                        '宣布' + serial[:8] + ' t4 ' + plan_path.parent.name + ' <=45min/35min cutoff；同一重启后U13，128清单顺序launch-only；授权=' + authorization], check=True)
        rc = subprocess.run([sys.executable, str(BASE / 't3/demo_board_run.py'), str(plan_path)]).returncode
        result_path = plan_path.parent / 'runner/board-run-result.json'
        result = read(result_path) if result_path.is_file() else {}
        if rc or result.get('before_unlock') != 0 or result.get('smoke') != 0:
            collect(out)
            raise RuntimeError('window failed; stop round, preserve runner lock disposition: ' + str(plan_path))
        expected = {key for s in plan['shards'] for key in expand(s['keys_file']).read_text().split()}
        actual = set()
        for shard in plan['shards']:
            actual.update(regress.records(plan_path.parent / 'runner' / shard['name']))
        if not expected <= actual:
            collect(out)
            raise RuntimeError('cutoff/missing key; partial facts retained, no silent full-round success')
    collect(out)
    # The ordinary 128-key round always finishes first; specials do not change that denominator.
    toutiao = config['special_slots']['toutiao']
    if toutiao.get('enabled'):
        special = out / 'toutiao-window'
        special.mkdir()
        plan = read(expand(config['windows'][0]))
        plan.update(serial=serial, why='Demo t4 reviewed Route B foreground desktop capture only',
                    out=portable(special / 'runner'), shards=[],
                    after_lock=[sys.executable, portable(HERE / 'round_identity.py'), '--round', portable(out),
                                '--out', portable(special / 'before-identity')],
                    before_unlock=[sys.executable, portable(HERE / 'round_identity.py'), '--round', portable(out),
                                   '--out', portable(special / 'after-identity')],
                    after_shards=[sys.executable, portable(HERE / 'foreground_toutiao.py'), '--round', portable(out)],
                    window_limit_minutes=30, stop_new_tests_by_minute=20)
        save(special / 'plan.json', plan)
        subprocess.run([str(WS / 'westlake-inputs/tools/board_note.sh'), 'progress',
                        str(MASTER / '.octos/boards/app-lighting.md'), '91', 'cx-t0',
                        '宣布61b头条独立前台点击窗<=30min；仅已部署SAFE Route B，不安装不换件'], check=True)
        subprocess.run([sys.executable, str(MASTER / 'scripts/lab/board_run.py'), str(special / 'plan.json')], check=True)
    boat = config['special_slots']['boatattack']
    if boat.get('enabled'):
        p = expand(boat['plan'])
        if regress.sha(p) != boat['plan_sha256']:
            raise ValueError('BoatAttack approved plan drift')
        subprocess.run([sys.executable, str(MASTER / 'scripts/lab/board_run.py'), str(p)], check=True)
    recorded_keys = len(read(out / 'batch-apps.json')['apps'])  # t5 subset: the actual run keys (<=128), not hardcoded
    (out / 'round-complete.json').write_text(json.dumps({'recorded_keys': recorded_keys, 'UI_verdict': 'pending_outer_review'}) + '\n')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--manifest', type=Path, default=BASE / 'demo-manifest.json')
    ap.add_argument('--tiers', type=Path, default=HERE / 'shot-tiers.json')
    ap.add_argument('--install-index', type=Path, default=BASE / 't3/install-index-final.json')
    ap.add_argument('--smoke', type=Path, default=MASTER / 'benchmark/2026-10-03-u13-stage-b/61b/smoke-61b.json')
    ap.add_argument('--boot-before', help='recorded boot ID before the user-approved reboot')
    ap.add_argument('--serial', choices=sorted(ALLOWED_SERIALS), default=SERIAL)
    ap.add_argument('--execute', action='store_true')
    ap.add_argument('--detach', action='store_true')
    ap.add_argument('--authorization', default='')
    a = ap.parse_args()
    if not a.execute:
        if a.detach:
            ap.error('--detach requires --execute')
        if not a.boot_before:
            ap.error('--boot-before required for offline preparation')
        prepare(a.manifest, a.tiers, a.install_index, a.out.resolve(), a.boot_before, a.smoke, serial=a.serial)
        return 0
    if read(a.out / 'round.json')['serial'] != a.serial:
        ap.error('--serial must match prepared round')
    if not a.authorization:
        ap.error('--execute requires --authorization; no lock taken')
    if a.detach:
        log = a.out / 'round.log'
        with log.open('x') as f:
            child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--out', str(a.out.resolve()),
                                      '--execute', '--serial', a.serial, '--authorization', a.authorization], stdout=f, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, start_new_session=True)
        print(json.dumps({'detached_pid': child.pid, 'log': str(log)}))
    else:
        tools = a.out / 'vm-tools'
        tools.mkdir(exist_ok=True)
        if not (tools / 'hdc').exists():
            (tools / 'hdc').write_text('#!/bin/sh\nexec orb -m a2hlab env WORKSPACES=' + shlex.quote(str(WS)) + ' MAC_HOME=' + shlex.quote(str(Path.home())) + ' bash ' + shlex.quote(str(WS / 'westlake-inputs/tools/hdc_mac.sh')) + ' \"$@\"\n')
            (tools / 'hdc').chmod(0o755)
        os.environ['PATH'] = str(tools.resolve()) + os.pathsep + os.environ['PATH']
        os.environ['WORKSPACES'] = str(WS)
        os.environ['MAC_HOME'] = str(Path.home())
        execute(a.out.resolve(), a.authorization)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
