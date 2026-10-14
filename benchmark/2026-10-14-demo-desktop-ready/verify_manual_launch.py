#!/usr/bin/env python3
"""Collect actual launcher clicks for the three historical ability fallbacks."""
import argparse
import json
from pathlib import Path
import shlex
import time
from capture_desktop import bms, ROOT

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--hdc', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    manifest = json.loads(a.manifest.read_text())
    packages = {'org.secuso.privacyfriendlycircuittraining', 'com.knirirr.beecount', 'com.rafapps.simplenotes'}
    apps = [x for x in manifest['apps'] if x['package'] in packages]
    assert len(apps) == 3 and all(x['disposition'] == 'keep' for x in apps)
    a.out.mkdir(parents=True, exist_ok=False)
    (a.out / 'commands').mkdir()
    board = bms.Board(manifest['serial'], shlex.quote(a.hdc),
                      'bash ' + shlex.quote(str(ROOT / 'scripts/lab/board_note.sh')),
                      'outer(codex)', a.out / 'commands')
    board.ready()
    result = {'serial': board.serial, 'boot': board.boot.strip(), 'apps': []}
    remote = '/data/local/tmp/manual-launch-' + str(int(time.time()))
    board.shell('mkdir ' + remote)
    for app in apps:
        out = a.out / app['key']
        out.mkdir()
        rec = {'key': app['key'], 'package': app['package'], 'launch_method': 'desktop_click_only', 'captured': []}
        try:
            bms.desktop_launch(board, {'package': app['package'], 'launch_activity': app['expected_desktop_ability']}, remote, out, rec, pages=12)
            time.sleep(5)
            rec['captured'].append(bms.capture(board, remote + '/t5.jpeg', out / 't5.jpeg'))
            rc, wm = board.shell('hidumper -s WindowManagerService -a "-a"', required=False)
            (out / 'windows.txt').write_text(wm)
            rec['window_dump_rc'] = rc
            rec['status'] = 'CLICK_AND_CAPTURE_PENDING_VISUAL_REVIEW'
        except bms.AppFailure as exc:
            rec['status'] = 'FAILED'
            rec['error'] = str(exc)
        bms.save(out / 'record.json', rec)
        result['apps'].append(rec)
        bms.save(a.out / 'results.json', result)
        print(app['key'], rec['status'], flush=True)
    board.shell('uitest uiInput keyEvent Home')
    print(json.dumps({'clicked': sum(bool(x.get('clicked')) for x in result['apps']), 'captures': sum(len(x['captured']) for x in result['apps'])}))

if __name__ == '__main__':
    main()
