#!/usr/bin/env python3
"""Stage the reviewed uid-dynamic slot; execute only from demo_seal_61b's context."""
import argparse
import json
import os
from pathlib import Path
import shlex
import sys

import demo_seal_61b as seal


ROOT = '/data/westlake-demo/toutiao'
CFG = '/system/etc/init/01_westlake_u13_toutiao.cfg'
DYNAMIC = {'reconcile_uid.sh', 'route-b-owner.sh', 'westlake-u13-toutiao-overlay.sh'}
MUTABLE = {'run.sh', 'preseed_metasec48.sh', 'prepare_jit50.sh', 'start-parent.sh', 'watchdog.sh', 'request.bin'}


def payload(reference, source_pins):
    path = seal.pinned(reference)
    document = seal.read(path)
    seal.require(document.get('board_serial') == seal.SERIAL and document.get('uid_mode') == 'installed-host-dynamic' and
                 set(document.get('reconciled_names', [])) == MUTABLE and
                 document.get('reconcile_readback', {}).get('request_offsets') == [312, 316],
                 'old/fixed-uid payload is not admissible')
    immutable = path.parent / 'immutable.tsv'
    seal.require(seal.sha(immutable) == document['immutable_tsv_sha256'], 'immutable list drift')
    rows = []
    for line in immutable.read_text().splitlines():
        fields = line.split()
        seal.require(len(fields) == 2 and seal.SHA.fullmatch(fields[0]), 'malformed immutable row')
        seal.board_path(fields[1])
        seal.require(Path(fields[1]).name not in MUTABLE, 'reconciled content must not be SHA-pinned: ' + fields[1])
        rows.append(fields)
    seal.require(rows and len({row[1] for row in rows}) == len(rows), 'empty/duplicate immutable inventory')
    approved = {Path(seal.expand(ref['path'])).name: ref['sha256'] for ref in source_pins}
    for name in DYNAMIC:
        seal.require(document.get('uid_dynamic_sources', {}).get(name, {}).get('sha256') == approved.get(name),
                     'uid-dynamic source not bound: ' + name)
    placements = document['placements']
    seal.require(len({row['target'] for row in placements}) == len(placements), 'duplicate placement target')
    for row in placements:
        source = Path(row['source'])
        seal.require(not source.is_absolute() and '..' not in source.parts, 'unsafe local payload member')
        seal.pinned(dict(path=str(path.parent / source), sha256=row['sha256']))
        target = seal.board_path(row['target'])
        seal.require(target.startswith(ROOT + '/scripts/') or target in (
                     '/system/etc/westlake-u13-toutiao-overlay.sh', CFG + '.disabled',
                     '/data/local/tmp/operator45/selfheal48/start-parent.sh',
                     '/data/local/tmp/operator45/selfheal48/spawn.sh',
                     '/data/local/tmp/operator45/selfheal48/screen-gate'), 'unexpected placement target')
        seal.require(row['mode'] == '0550', 'unexpected mode')
    targets = {row['target'] for row in placements}
    seal.require(all(ROOT + '/scripts/' + name in targets for name in DYNAMIC) and CFG + '.disabled' in targets,
                 'dynamic sources/cfg missing from placements')
    seal.require(all(row['target'] in {item[1] for item in rows} for row in placements
                     if not row.get('inactive') and Path(row['target']).name not in MUTABLE), 'unprotected immutable placement')
    return path.parent, document, rows


def stage(plan, document, directory, immutable, transport, boot_id, plan_sha):
    hdc = plan['hdc']

    def command(name, argv):
        code, output = transport.run(name, argv)
        seal.require(code == 0, name + ' exit=' + str(code) + '; slot remains disabled on refusal')
        return output

    def shell(name, text):
        return command(name, [hdc, '-t', seal.SERIAL, 'shell', text])

    seal.require(shell('tt-boot-before', seal.BOOT).strip() == boot_id, 'Toutiao stage boot drift')
    host_uid = shell('tt-host-uid', 'stat -c %u /data/app/el2/100/base/org.westlake.imehost').strip()
    seal.require(host_uid.isascii() and host_uid.isdecimal(), 'installed host UID must be numeric')
    shell('tt-disabled', 'mkdir -p ' + ROOT + '/scripts && touch ' + ROOT + '/DISABLED && test -f ' + ROOT + '/DISABLED')
    staged_system = {}
    for row in document['placements']:
        target = row['target']
        if target.startswith('/system/'):
            target = ROOT + '/staged-system/' + Path(target).name
            staged_system[row['target']] = target
        shell('tt-mkdir', 'mkdir -p ' + shlex.quote(str(Path(target).parent)))
        command('tt-stage', [hdc, '-t', seal.SERIAL, 'file', 'send', str(directory / row['source']), target])
        shell('tt-mode', 'chmod 0550 ' + shlex.quote(target))
        output = shell('tt-stage-sha', 'sha256sum ' + shlex.quote(target))
        seal.require(output.split() == [row['sha256'], target], 'placement SHA mismatch: ' + target)
    command('tt-stage-immutable', [hdc, '-t', seal.SERIAL, 'file', 'send', str(directory / 'immutable.tsv'), ROOT + '/immutable.tsv'])
    shell('tt-immutable-mode', 'chmod 0444 ' + ROOT + '/immutable.tsv')
    shell('tt-reconcile', '/system/bin/sh ' + ROOT + '/scripts/reconcile_uid.sh > ' + ROOT +
          '/reconcile-seal.log 2>&1 && tail -n 1 ' + ROOT + '/reconcile-seal.log')
    got = shell('tt-reconcile-readback', 'tail -n 1 ' + ROOT + '/reconcile-seal.log').strip()
    seal.require(got == host_uid, 'reconcile readback differs from installed host UID')
    for digest, target in immutable:
        staged_target = staged_system.get(target, target)
        actual = shell('tt-immutable-readback', 'sha256sum ' + shlex.quote(staged_target))
        seal.require(actual.split() == [digest, staged_target], 'reconcile changed immutable/missing donor: ' + target)
    seal.require(shell('tt-boot-before-enable', seal.BOOT).strip() == boot_id, 'boot drift before ENABLE')
    placements = ''
    for target, staged_target in staged_system.items():
        placements += 'cp ' + shlex.quote(staged_target) + ' ' + shlex.quote(target) + '; chown 0:0 ' + shlex.quote(target) + \
                      '; chmod 0550 ' + shlex.quote(target) + '; chcon u:object_r:system_etc_file:s0 ' + shlex.quote(target) + \
                      '; cmp ' + shlex.quote(staged_target) + ' ' + shlex.quote(target) + '; '
    shell('tt-cfg-enable', "set -eu; reseal=0; trap 'rc=$?; if [ \"$reseal\" = 1 ]; then mount -o ro,remount / || rc=1; fi; if [ \"$rc\" != 0 ]; then touch " + ROOT +
          "/DISABLED; fi; exit \"$rc\"' EXIT; "
          "opts=$(grep ' / ' /proc/mounts | head -n1 | cut -d' ' -f4); "
          "case ,$opts, in *,rw,*) ;; *) mount -o rw,remount /; reseal=1;; esac; " +
          placements + "cp " + CFG + '.disabled ' + CFG + '; chown 0:0 ' + CFG + '; chmod 0550 ' + CFG +
          '; chcon u:object_r:system_etc_file:s0 ' + CFG +
          '; cmp ' + CFG + '.disabled ' + CFG + '; rm -f ' + ROOT + '/DISABLED; test ! -e ' + ROOT + '/DISABLED')
    return dict(serial=seal.SERIAL, plan_sha256=plan_sha, boot_id=boot_id, enabled=True,
                uid_mode='installed-host-dynamic', host_uid=host_uid, reconcile_checked=True,
                immutable_preserved=True, cfg=CFG, app_launch_operations=0)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    if not args.execute:
        print('DRY-RUN: stage reviewed dynamic worker/reconciler/owner + inactive cfg; exclude six reconciled names from immutable; reconcile/readback + immutable verify; ENABLE=place active cfg + rm DISABLED. No board access.')
        return 0
    try:
        path = Path(os.environ['DEMO_SEAL_PLAN'])
        plan_sha = os.environ['DEMO_SEAL_PLAN_SHA']
        seal.require(seal.sha(path) == plan_sha and os.environ['DEMO_SEAL_SERIAL'] == seal.SERIAL and
                     os.environ['DEMO_SEAL_STEP'] == 'toutiao_slot', 'not a reviewed orchestration context')
        plan = seal.read(path)
        seal.require(plan.get('execution_enabled') is True and not plan.get('pending'), 'disabled/pending orchestration')
        provider = plan['providers']['toutiao_slot']
        for ref in provider['pins']:
            seal.pinned(ref)
        directory, document, immutable = payload(plan['toutiao_slot']['placement'], provider['pins'])
        out = Path(os.environ['DEMO_SEAL_OUT'])
        raw = out / 'toutiao-slot-raw'
        raw.mkdir(exist_ok=False)
        boot = os.environ['DEMO_SEAL_BOOT_ID']
        seal.require(seal.UUID.fullmatch(boot), 'valid current bare boot required')
        receipt = stage(plan, document, directory, immutable, seal.Transport(raw, 120), boot, plan_sha)
        (out / 'toutiao_slot.json').write_text(json.dumps(receipt, indent=2) + '\n')
        return 0
    except (KeyError, OSError, ValueError, TypeError) as error:
        print('TT-SLOT-STOP: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
