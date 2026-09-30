#!/usr/bin/env python3
"""Bring a clean OH 6.1.0.31 DAYU600 up to the lab's unified state, checking every step against a known-good board.

    bringup_clean_board.py plan
    bringup_clean_board.py check <serial>                  read-only gates: whitelist, online, ROM, aarch64, 47-lib firmware
    bringup_clean_board.py diff  <serial> [--ref 5ea]      read-only: inventory the board, diff against a reference
                                                           inventory, and name the local package file that supplies
                                                           each missing or different file (matched by sha256)

The board-writing steps are the existing, reviewed tools (listed by `plan`); this script only decides whether a
board is where it should be. It has not yet been run end to end on a clean board: the three lab boards were built
up in layers (PR03 restore -> B79/B89 installers -> FZ-001 -> generations), so on the first clean board expect to
walk `diff` output back into missing steps, then record them here and in env.md.

Reference inventories: benchmark/2026-09-30-board-inventory/<label>/ (board_inventory.sh on the U2 boards).
Firmware gate: knowledge/firmware/oh61-firmware-libs.sha256 (47 libs the runtime links against, from
westlake native/oh61-firmware-abi.json).
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lab_paths  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
HDC = os.environ.get('HDC', '/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc')
ROM = 'OpenHarmony-6.1.0.31'
INVENTORIES = REPO / 'benchmark/2026-09-30-board-inventory'
FIRMWARE = REPO / 'knowledge/firmware/oh61-firmware-libs.sha256'
# files that legitimately differ between lab boards (experiment leftovers, not part of the unified state)
BOARD_SPECIFIC = {'/system/etc/init/wl_toutiao.cfg', '/system/etc/init/wl_toutiao.cfg.disabled'}

PLAN = """\
Clean board -> unified state U2 (run from <workspaces>/westlake-harness; lock the board first:
  board_note.sh lock <abs board.md> <serial> <lane> "bring-up").  Add the board to knowledge/boards.json first.
 0  [read-only]   bringup_clean_board.py check <serial>                      ROM + 47-lib firmware gate must pass
 1  [board write] scripts/lab/board_setup.sh <serial>                        clock, screen-off timeout, unlock, host HAP, framework stage
                  then join WiFi in the board UI (no CLI on the board)
 2  [board write] bms/.agents/skills/reproduce-helloworld/scripts/reproduce.sh restore <serial>
                  PR03 BMS route on the factory system (payload: $HOME/orca/.bridge-payload)
 3  [board write] scripts/lab/swap_installer.py dry-run|apply|restart|verify --serial <serial>
                  FZ-001 installer pair 6aadb8b4/7048c7c5; if step 2 left a pair other than the B89 baseline, pass
                  --accept-baseline <libbms_sha>:<libapk_sha> (read them from `diff`); foundation restarts, a hub
                  board may drop off USB
 4  [board write] in the VM: <workspaces>/westlake-harness-bms-deploy/scripts/lab/deploy_generation.sh <serial> \\
                  <workspaces>/westlake-generation-v3c-candidate --lane <lane>                      (base generation)
 5  [board write] same, <workspaces>/westlake-generation-n2-51a78bde --upgrade                     (native N2)
 6  [board write] JAR J2: push <workspaces>/vm-copies/j2-0715c964/oh-adapter-runtime.jar to
                  /data/local/tmp/j2-0715c964/ and mount --bind it over /system/android/framework/oh-adapter-runtime.jar
                  (not persistent: redo after every reboot)
 7  [read-only]   bringup_clean_board.py diff <serial>                       must report 0 missing / 0 different
 8  [board]       bms_batch.py --execute --serial <serial> --keys <shard> --reinstall --hilog --shots 5,20
                  facts.txt must start with RUNTIME fingerprint=937e2a6d0d88 (U2); read t20 screenshots vs U2's 24 lit
Never kill -9 appspawn-x (init crashes, the board drops); use begetctl stop_service/start_service.
"""


def shell(serial, cmd, timeout=600):
    r = subprocess.run([HDC, '-t', serial, 'shell', cmd], capture_output=True, text=True, timeout=timeout)
    return r.stdout.replace('\r', '')


def parse_sums(text):
    out = {}
    for line in text.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and len(parts[0]) == 64:
            out[parts[1].strip()] = parts[0]
    return out


def check(serial):
    results = []
    boards = lab_paths.boards('oh')
    results.append(('whitelisted in knowledge/boards.json', serial in boards, boards.get(serial, 'not listed')))
    targets = subprocess.run([HDC, 'list', 'targets'], capture_output=True, text=True).stdout.split()
    online = serial in targets
    results.append(('online (hdc list targets)', online, ''))
    if online:
        rom = shell(serial, 'param get const.ohos.fullname').strip()
        results.append((f'ROM is {ROM}', rom == ROM, rom))
        arch = shell(serial, 'uname -m').strip()
        results.append(('aarch64', arch == 'aarch64', arch))
        want = parse_sums(FIRMWARE.read_text())
        got = parse_sums(shell(serial, 'sha256sum ' + ' '.join(want)))
        bad = [p for p in want if got.get(p) != want[p]]
        results.append((f'firmware gate ({len(want)} libs)', not bad, f'{len(want) - len(bad)}/{len(want)} match'
                        + (f'; first mismatch {bad[0]}' if bad else '')))
    for name, ok, note in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}  {note}")
    return 0 if all(ok for _, ok, _ in results) else 1


def provenance(needed):
    """{sha256: [local files with that content]} over the lab's package dirs, hashing only size-matched files."""
    ws = lab_paths.workspaces()
    roots = [p for p in ws.glob('westlake-generation-*') if p.is_dir()]
    roots += [p for p in ws.glob('westlake-installer-*') if p.is_dir()]
    roots += [ws / 'vm-copies', ws / 'westlake-bms-suite/.bridge-payload', Path.home() / 'orca/.bridge-payload']
    sizes = {s for s, _ in needed.values()}
    want = {h for _, h in needed.values()}
    found = {}
    for root in roots:
        if not root.is_dir():
            continue
        for dirpath, _, names in os.walk(root):
            for n in names:
                p = Path(dirpath) / n
                try:
                    if p.is_symlink() or p.stat().st_size not in sizes:
                        continue
                    h = hashlib.sha256(p.read_bytes()).hexdigest()
                except OSError:
                    continue
                if h in want:
                    shown = (f'<workspaces>/{p.relative_to(ws)}' if p.is_relative_to(ws)
                             else f'~/{p.relative_to(Path.home())}' if p.is_relative_to(Path.home()) else str(p))
                    found.setdefault(h, []).append(shown)
    return found


def diff(serial, ref, out):
    ref_dir = INVENTORIES / ref
    if not ref_dir.is_dir():
        sys.exit(f'no reference inventory {ref_dir}')
    out = Path(out) if out else Path(tempfile.mkdtemp(prefix=f'inventory-{serial[:8]}-'))
    subprocess.run([str(REPO / 'scripts/lab/board_inventory.sh'), serial, str(out)], check=True,
                   stdout=subprocess.DEVNULL)
    sizes = {}
    for line in (ref_dir / 'system-files.txt').read_text().splitlines():
        parts = line.split(None, 2)
        if len(parts) == 3:
            sizes[parts[2]] = int(parts[0])
    report = {'serial': serial, 'reference': ref, 'inventory': str(out)}
    needed = {}
    for name in ('system.sha256', 'android.sha256'):
        want = parse_sums((ref_dir / name).read_text())
        got = parse_sums((out / name).read_text())
        missing = sorted(p for p in want if p not in got and p not in BOARD_SPECIFIC)
        different = sorted(p for p in want if p in got and got[p] != want[p] and p not in BOARD_SPECIFIC)
        extra = sorted(p for p in got if p not in want and p not in BOARD_SPECIFIC)
        report[name] = {'missing': missing, 'different': different, 'extra': extra}
        for p in missing + different:
            needed[p] = (sizes.get(p, -1), want[p])
    found = provenance(needed) if needed else {}
    report['sources'] = {p: found.get(h, []) for p, (_, h) in needed.items()}
    (out / 'diff.json').write_text(json.dumps(report, indent=2) + '\n')
    for name in ('system.sha256', 'android.sha256'):
        r = report[name]
        print(f"{name}: {len(r['missing'])} missing, {len(r['different'])} different, {len(r['extra'])} extra")
    for p, srcs in sorted(report['sources'].items()):
        print(f"  {p}  <- {srcs[0] if srcs else 'NO LOCAL SOURCE'}" + (f' (+{len(srcs) - 1})' if len(srcs) > 1 else ''))
    print(f'details: {out / "diff.json"}')
    return 0 if not needed else 1


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('plan')
    c = sub.add_parser('check'); c.add_argument('serial')
    d = sub.add_parser('diff'); d.add_argument('serial'); d.add_argument('--ref', default='5ea'); d.add_argument('--out')
    a = ap.parse_args(argv)
    if a.cmd == 'plan':
        print(PLAN, end='')
        return 0
    if a.cmd == 'check':
        return check(a.serial)
    return diff(a.serial, a.ref, a.out)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
