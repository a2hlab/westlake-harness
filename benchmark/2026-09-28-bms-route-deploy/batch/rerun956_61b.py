"""#38 ④: for the 23 install-failed-9568260 keys on 61b —
bm uninstall (drop the #23-era old install) -> reinstall the same input APK
-> full collect_app chain (install/bm dump/cold stop/sandbox/gated desktop
launch/t3+final captures/process census). Per-key receipts; summary results.
Faultlog pull+mapping happens after this run, separately.
"""
import json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import bms_batch as b
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts/lab'));import lab_paths  # <repo>/scripts/lab

SERIAL = '61b0657200000000000000000324012c'
LANE = 'oc-t4'
RUN = 'b4-38-rerun956-61b-20260928T2350'
out = Path.home() / 'a2hlab/board' / RUN
out.mkdir(parents=True, exist_ok=False)
un_dir = out / 'uninstall'; un_dir.mkdir()
board = b.Board(SERIAL, str(lab_paths.tools()/'hdc_mac.sh'),
                'mac '+str(lab_paths.tools()/'board_note.sh'), LANE, out / 'commands')
board.ready()
manifest = {a['key']: a for a in json.load(open(ROOT / 'apps.json'))['apps']}
if len(sys.argv) > 1 and sys.argv[1] == '--keys':
    keys = sys.argv[2].split(',')
else:
    keys = [r['key'] for r in json.load(open(
        Path.home()/'a2hlab/board/b4-36-faultlog/b4-final.json'))['records']
        if r['category'] == 'install-failed-9568260']
print('keys:', len(keys), keys, flush=True)
summary = []
for i, k in enumerate(keys):
    app = manifest[k]
    # x/noice have package=None in apps.json; resolve like collect_app does
    try:
        app = b.resolve_input(Path.home() / 'a2hlab/app-inputs', app)
    except b.AppFailure as e:
        app = dict(app, package=app.get('package') or '')
    rec = {'key': k, 'package': app.get('package'), 'started_at': time.time()}
    if not app.get('package'):
        rec['status'] = 'input_unresolvable'; rec['error'] = 'no package in apps.json and resolve_input failed'
        summary.append(rec); b.save(out / 'results.json', {'run': RUN, 'serial': SERIAL, 'done': len(summary),
                                  'total': len(keys), 'trials': summary})
        print('%d/%d %s -> %s' % (i + 1, len(keys), k, rec['status']), flush=True)
        continue
    d = out / k  # collect_app creates it (mkdir exist_ok=False) — never pre-create
    remote = '/data/local/tmp/' + RUN + '/' + k
    board.shell('mkdir -p ' + remote)
    rec = {'key': k, 'package': app['package'], 'started_at': time.time()}
    rc, un = board.shell('bm uninstall -n ' + app['package'], required=False)
    # receipts live under <run>/uninstall/<key>.txt, never inside the app dir
    (un_dir / (k + '.txt')).write_text(un); rec['uninstall'] = un.strip()[:160]
    try:
        r = b.collect_app(board, app, Path.home() / 'a2hlab/app-inputs', d, remote)
        rec.update({x: r.get(x) for x in ('status', 'bms', 'observed_pids', 'foreground') if x in r})
        rec['install'] = r.get('install')
        rec['screenshots'] = r.get('screenshots', [])
    except b.AppFailure as e:
        rec['status'] = 'app_failed'; rec['error'] = repr(e)[:240]
    except b.BatchStop as e:
        rec['status'] = 'batch_stopped'; rec['error'] = repr(e)[:240]
        d.mkdir(parents=True, exist_ok=True)  # collect_app may not have created it
        summary.append(rec); b.save(d / 'record.json', rec)
        b.save(out / 'results.json', {'run': RUN, 'serial': SERIAL, 'done': len(summary),
                                      'total': len(keys), 'trials': summary})
        print('BATCHSTOP at %s: %r' % (k, e), flush=True)
        sys.exit(3)
    rec['finished_at'] = time.time()
    summary.append(rec)
    b.save(d / 'record.json', rec)
    b.save(out / 'results.json', {'run': RUN, 'serial': SERIAL, 'done': len(summary),
                                  'total': len(keys), 'trials': summary})
    print('%d/%d %s -> %s' % (i + 1, len(keys), k, rec.get('status')), flush=True)
print('DONE', len(summary), flush=True)
