import argparse
import hashlib
import json
import os
from pathlib import Path
import tarfile


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
OLD = '2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0'
NEW = '51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5'
SERIAL = '5cd1e3dd00000000000000000923012c'
TARGETS = ['/system/lib64/libinstalls.z.so', '/system/lib64/platformsdk/libinstalls.z.so']


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


def fingerprint(values, paths):
    lines = sorted(f'{values[path]}  {path}' for path in paths)
    return hashlib.sha256('\n'.join(lines).encode()).hexdigest()[:12]


def build(workspaces):
    workspaces = Path(workspaces).resolve()
    kit = workspaces / 'oh61-bms-kit-b79'
    receipts = workspaces / 'westlake-harness-bms-deploy/benchmark/2026-09-29-install-wall-validation'
    ledger = json.loads((receipts / 'source-toolchain.json').read_text())
    pinned = []

    def pin(path, expected=None, role='provenance'):
        actual = sha(path)
        if expected and actual != expected:
            raise ValueError(f'archive drift: {path.name}: expected={expected} actual={actual}')
        pinned.append(dict(role=role, path='$WORKSPACES/' + str(path.relative_to(workspaces)), sha256=actual))

    pin(kit / 'board-baseline/libinstalls.z.so', OLD, 'original')
    pin(kit / 'out/wukong100/bundlemanager/bundle_framework/libinstalls.z.so', NEW, 'candidate')
    pin(workspaces / 'oh61-bms-kit-b79-r3-final.tar.gz',
        '61ff2def4508cafa6c1acd30c0c8436a5a760d5869a3520a140a216e39548bb6', 'complete_source_archive')
    drift = []
    for relative, expected in ledger.items():
        actual = sha(kit / relative)
        if actual == expected:
            pin(kit / relative, expected, 'source_or_toolchain')
        else:
            with tarfile.open(workspaces / 'oh61-bms-kit-b79-r3-final.tar.gz') as archive:
                member = 'oh61-bms-kit-b79/' + relative
                stream = archive.extractfile(member)
                frozen = hashlib.sha256(stream.read()).hexdigest()
            if frozen != expected:
                raise ValueError('frozen archive source drift: ' + relative)
            drift.append(dict(path='$WORKSPACES/oh61-bms-kit-b79/' + relative, actual_sha256=actual,
                              frozen_sha256=frozen, archive_member=member,
                              disposition='Mutable unpacked file is not accepted as source; frozen archive member matches historical receipt. No rebuild.'))
    for relative in ['source-toolchain.json', 'build_narrow.sh', 'candidate.sha256',
                     'patches/0001-reuse-manifest-1mib.patch', 'patches/0002-native-exact-payloads.patch',
                     'build.log', 'build-resume.log', 'build-r2.log', 'build-r3.log', 'build-r4.log',
                     'build-r5.log', 'build-r6.log', 'build-r7.log', 'archive-r3-remote.sha256']:
        pin(receipts / relative, role='historical_build_receipt')
    provenance = dict(schema='spare-installer-provenance/v1', device_access=False, rebuild=False,
                      verified_local_files=pinned, unpacked_source_drift=drift,
                      source_patch_commit='22de5ddb52212f3640a7214194472e30991e0c65',
                      approval_refresh_commit='e89d1af4fe7a29c4d095d5cebcb6367c3c87474f',
                      final_source_build_commit='70fc62aa7e0369427f4ba22b1d370d2a58496eab',
                      remote_archive='$LAB_HOME/westlake-oh6.1-b79-bms-2220df48-installs-51e1b525/oh61-bms-kit-b79-r3-final.tar.gz',
                      remote_archive_status='historical matching receipt; no fresh SSH',
                      historical_recipe='build_narrow.sh; frozen clang b107ce03; ninja -d keeprsp -v -j2',
                      caveat='Historical logs include failed rounds. R2 first produced 51e1; R3 modified companion BMS only. No new build or byte-reproduction claim.')
    journal = workspaces / 'westlake-harness-u7-executor/benchmark/2026-10-03-u14-stage-a-plan/window2/u14-A2-20261003T131427/61b/transaction/transaction/journal.json'
    plan = json.loads(journal.read_text())['plan']
    expected = plan['baseline']
    references = plan['reference_paths']
    if len(expected) != 319 or fingerprint(expected, references['runtime']) != '452447a4a0ba' or fingerprint(expected, references['boot']) != 'ee927db88a67':
        raise ValueError('61b recovery reference drift')
    reference = dict(schema='spare-installer-reference/v1', expected_paths=expected, reference_paths=references,
                     runtime='452447a4a0ba', boot='ee927db88a67', source='$WORKSPACES/' + str(journal.relative_to(workspaces)),
                     source_sha256=sha(journal), source_role='U13 restored baseline, not U14 candidate expected')
    output = dict(schema='spare-installer-plan/v1', execution_enabled=False, rollout_ready=False,
                  serial=SERIAL, later_board='5ea34a4500000000000000001123012c', later_board_enabled=False,
                  candidate=provenance['verified_local_files'][1], original=provenance['verified_local_files'][0],
                  targets=TARGETS, only_mutable_system_paths=TARGETS,
                  offline_precheck={'expect': {
                      'confirm': 'Both physical aliases survive reboot at 51e1, all319 U13 paths match, runtime452447a4/boot ee927db8; init-owned AppSpawnX and HW/ZZ signed lit t20.',
                      'refute': 'Either alias drifts, any path mismatch, daemon absent/non-init-owned or HW/ZZ white. Keep lock; no Mac repair counted as autonomous PASS.'}},
                  acceptance_blocker='0178de5c0e: 61b autonomous replay319/319 but AppSpawnX daemon absent; two control screenshots white. Installer unification alone does not prove reboot lighting.',
                  pending=['outer approved5cd time window', 'fresh boot-bound approval and existing lock',
                           'pristine U13 without Boat/private overlays', 'independent init daemon startup resolution', 'human t20 control signoff'])
    return provenance, reference, output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspaces', type=Path, default=Path(os.environ.get('WORKSPACES', REPO.parent)))
    args = parser.parse_args()
    provenance, reference, plan = build(args.workspaces)
    for name, value in [('provenance.json', provenance), ('reference.json', reference), ('plan.json', plan)]:
        save(HERE / name, value)
    print(json.dumps(dict(device_access=False, archive_files=len(provenance['verified_local_files']), identity_paths=319,
                          candidate_sha256=NEW, execution_enabled=False)))


if __name__ == '__main__':
    main()
