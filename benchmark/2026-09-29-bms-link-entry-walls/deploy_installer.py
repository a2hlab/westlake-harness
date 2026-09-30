"""5cd-only libapk_installer swap, the #52/#55 way, with backup and rollback.

  python3 deploy_installer.py apply     # 675536e8 (B3) -> B7 build, both paths, restart foundation
  python3 deploy_installer.py rollback  # restore the backed-up B3 library, restart foundation
  python3 deploy_installer.py status    # read-only

Both copies are replaced by an atomic rename of a same-directory temp file (the
running foundation keeps its mapped inode until the restart). The root mount is
put back to its prior ro/rw state. Completion additionally needs a non-black
desktop screenshot (black = 36627 B); if black, reboot and re-run the restore.
"""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-09-28-bms-route-deploy' / 'batch'))
import bms_batch as b  # noqa: E402
sys.path.insert(0, str(HERE.parents[1] / 'scripts' / 'lab'))
import lab_paths  # noqa: E402

SERIAL = '5cd1e3dd00000000000000000923012c'
HDC = '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
LOCK = str(lab_paths.tools() / 'board_note.sh')
PATHS = ['/system/lib64/libapk_installer.so', '/system/lib64/platformsdk/libapk_installer.so']
BASELINE = '675536e8a43ac747cbffc0e130d5681ba7bcf2bd3fd305f3d0d357ca797a793d'   # B3, current on 5cd
NEW = '1ebf78ab2bbe4573dfbe146b9f99e6b06e3a581fb9d16721c2272bc18e6cdfa5'        # B7 (DECLARED_XML_ONLY)
NEW_VM = 'a2hlab/build-runs/20260929-oh6.1.0.31-b7/installer/libapk_installer.b7.so'  # under the VM user's home
BACKUP = '/data/local/tmp/b7-installer-backup'


def hashes(bd, pid=None):
    paths = PATHS + ([f'/proc/{pid}/root{p}' for p in PATHS] if pid else [])
    _, text = bd.shell('sha256sum ' + ' '.join(paths))
    return {l.split()[1]: l.split()[0] for l in text.splitlines() if len(l.split()) == 2}


def foundation(bd):
    _, ps = bd.shell('ps -A -o PID,PPID,UID,NAME')
    pids = [r['pid'] for r in b.processes(ps) if r['name'] == 'foundation']
    assert len(pids) == 1, pids
    return pids[0]


def swap(bd, source, receipt):
    _, root = bd.shell('mount | grep " on / "')
    was_ro = '(ro,' in root
    receipt['root_was_ro'] = was_ro
    if was_ro:
        bd.shell('mount -o rw,remount /')
    try:
        for p in PATHS:
            tmp = p + '.b7-new'
            bd.shell(f'test ! -e {tmp} && cp {source} {tmp} && chown 0:0 {tmp} && chmod 0755 {tmp} '
                     f'&& chcon u:object_r:system_lib_file:s0 {tmp} && mv -f {tmp} {p}')
        bd.shell('sync')
    finally:
        if was_ro:
            bd.shell('mount -o ro,remount /', required=False)
    receipt['swapped'] = hashes(bd)


def restart_foundation(bd, receipt):
    receipt['foundation_before'] = foundation(bd)
    bd.shell('begetctl stop_service foundation')
    bd.shell('begetctl start_service foundation')
    import time
    for _ in range(30):
        time.sleep(2)
        try:
            pid = foundation(bd)
        except AssertionError:
            continue
        if pid != receipt['foundation_before']:
            receipt['foundation_after'] = pid
            return pid
    raise b.BatchStop('foundation did not come back')


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'status'
    out = HERE / 'runs' / ('installer-' + mode + '-' +
                           subprocess.check_output(['date', '+%Y%m%dT%H%M%S']).decode().strip())
    bd = b.Board(SERIAL, HDC, LOCK, 'cc-t3', out / 'commands')
    bd.ready()
    receipt = {'mode': mode, 'serial': SERIAL, 'boot_id': bd.boot, 'before': hashes(bd, foundation(bd))}
    if mode == 'apply':
        assert set(receipt['before'].values()) == {BASELINE}, receipt['before']
        bd.shell(f'test ! -e {BACKUP} && mkdir {BACKUP}')
        for i, p in enumerate(PATHS):
            bd.shell(f'cp -p {p} {BACKUP}/{i}.so')
        _, text = bd.shell(f'sha256sum {BACKUP}/0.so {BACKUP}/1.so')
        assert all(l.split()[0] == BASELINE for l in text.splitlines() if l.strip()), text
        local = out / 'libapk_installer.b7.so'
        subprocess.run(['orb', '-m', 'a2hlab', 'cat', lab_paths.vm_home() + '/' + NEW_VM], stdout=local.open('wb'), check=True)
        assert b.sha(local) == NEW
        bd.send(local, BACKUP + '/new.so')
        _, text = bd.shell(f'sha256sum {BACKUP}/new.so')
        assert text.split()[0] == NEW, text
        swap(bd, BACKUP + '/new.so', receipt)
        expect = NEW
    elif mode == 'rollback':
        _, text = bd.shell(f'sha256sum {BACKUP}/0.so')
        assert text.split()[0] == BASELINE, text
        swap(bd, BACKUP + '/0.so', receipt)
        expect = BASELINE
    else:
        print(json.dumps(receipt, indent=2)); return
    pid = restart_foundation(bd, receipt)
    receipt['after'] = hashes(bd, pid)
    assert set(receipt['after'].values()) == {expect} and len(receipt['after']) == 4, receipt['after']
    _, maps = bd.shell(f'grep libapk_installer /proc/{pid}/maps', required=False)
    receipt['foundation_maps_installer'] = maps.strip().splitlines()[:2]
    receipt['desktop'] = b.capture(bd, BACKUP + '/desktop.jpeg', out / 'desktop.jpeg')
    receipt['desktop']['black_36627'] = receipt['desktop']['remote_stat'].split()[0] == '36627'
    b.save(out / 'receipt.json', receipt)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
