"""5cd-only runtime JAR overlay with pinned baseline and explicit rollback (B5 method).

  python3 deploy.py apply     # bind-mount the B7 JAR over /system/android/framework/oh-adapter-runtime.jar
  python3 deploy.py rollback  # umount it and prove the baseline hash is back
  python3 deploy.py status    # read-only

The runtime JAR is loaded per child through a PathClassLoader after fork (not in
the boot image, not mapped by the appspawn-x daemon), so new children pick the
overlay up without restarting anything. The mount is not reboot-persistent.
"""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-09-28-bms-route-deploy' / 'batch'))
import bms_batch as b  # noqa: E402

SERIAL = '5cd1e3dd00000000000000000923012c'
HDC = '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
LOCK = str(Path.home() / 'orca/workspaces/westlake-inputs/tools/board_note.sh')
TARGET = '/system/android/framework/oh-adapter-runtime.jar'
REMOTE_DIR = '/data/local/tmp/b7-walls'
BUILD = json.loads((HERE / 'build-result.json').read_text())


def board():
    out = HERE / 'runs' / ('deploy-' + subprocess.check_output(['date', '+%Y%m%dT%H%M%S']).decode().strip())
    bd = b.Board(SERIAL, HDC, LOCK, 'cc-t3', out / 'commands')
    bd.ready()
    return bd, out


def target_hash(bd):
    _, text = bd.shell('sha256sum ' + TARGET)
    return text.split()[0]


def mounted(bd):
    _, text = bd.shell('cat /proc/self/mountinfo')
    return [l for l in text.splitlines() if (' ' + TARGET + ' ') in l]


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'status'
    bd, out = board()
    receipt = {'mode': mode, 'serial': SERIAL, 'boot_id': bd.boot,
               'before_sha256': target_hash(bd), 'mounts_before': mounted(bd)}
    if mode == 'apply':
        assert receipt['before_sha256'] == BUILD['baseline_sha256'], receipt
        assert not receipt['mounts_before'], 'target already has a mount; roll back first'
        local = out / 'oh-adapter-runtime.jar'
        subprocess.run(['orb', '-m', 'a2hlab', 'cat', BUILD['output']], stdout=local.open('wb'), check=True)
        assert b.sha(local) == BUILD['output_sha256']
        bd.shell('mkdir -p ' + REMOTE_DIR)
        bd.send(local, REMOTE_DIR + '/oh-adapter-runtime.jar')
        staged = REMOTE_DIR + '/oh-adapter-runtime.jar'
        _, check = bd.shell('sha256sum ' + staged)
        assert check.split()[0] == BUILD['output_sha256'], check
        bd.shell('chmod 0644 ' + staged + '; chcon u:object_r:system_file:s0 ' + staged
                 + '; mount --bind ' + staged + ' ' + TARGET)
        receipt['after_sha256'] = target_hash(bd)
        assert receipt['after_sha256'] == BUILD['output_sha256'], receipt
    elif mode == 'rollback':
        if receipt['mounts_before']:
            bd.shell('umount ' + TARGET)
        receipt['after_sha256'] = target_hash(bd)
        assert receipt['after_sha256'] == BUILD['baseline_sha256'], receipt
        assert not mounted(bd), 'overlay still mounted'
    receipt['mounts_after'] = mounted(bd)
    b.save(out / 'receipt.json', receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
