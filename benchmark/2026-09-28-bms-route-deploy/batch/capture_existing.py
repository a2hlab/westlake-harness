#!/usr/bin/env python3
"""Supplement interrupted/alias-missed captures using an exact prior installed APK.

No install, uninstall, or runtime changes. Prior successful install is explicit
provenance; a failed reinstall is retained and never relabeled successful.
"""
import argparse
import json
from pathlib import Path
import shlex
import sys
import time
import bms_batch as b
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'scripts/lab'));import lab_paths  # <repo>/scripts/lab


def capture(board, entry, input_root, out, remote, prior_path):
    prior=json.loads(Path(prior_path).read_text())
    app=b.resolve_input(input_root,entry)
    if (prior.get('key')!=entry['key'] or prior.get('serial')!=board.serial or
        prior.get('package')!=app['package'] or prior.get('apk_sha256')!=app['apk_sha256'] or
        (prior.get('install') or {}).get('return_code')!=0 or not (prior.get('install') or {}).get('success_text')):
        raise b.AppFailure('no matching prior successful install receipt')
    out.mkdir(parents=True,exist_ok=False)
    rec=dict(app,serial=board.serial,boot_id=board.boot,status='started',
        mode='capture_existing_exact_apk',install=None,bms={'queryable':False},
        screenshots=[],launch_method='desktop',clicked=False,review='pending_review',
        prior_successful_install={'path':str(prior_path),'sha256':b.sha(prior_path)})
    uid=None
    validated=False
    try:
        _,text=board.shell('bm dump -n '+shlex.quote(app['package']))
        (out/'bundle.txt').write_text(text);rec['bms']=b.parse_bundle(text,app['package']);uid=rec['bms']['uid']
        path='/data/app/el1/bundle/public/'+app['package']+'/android/base.apk'
        _,digest=board.shell('sha256sum '+shlex.quote(path));(out/'existing-apk-hash.txt').write_text(digest)
        if not digest.split() or digest.split()[0]!=app['apk_sha256']:
            raise b.AppFailure('installed APK does not match original input')
        validated=True
        board.shell('mkdir -p '+shlex.quote(remote))
        if not b.cold_stop(board,app['package'],uid,out):raise b.AppFailure('cold state unconfirmed')
        rec['sandbox_preparation']=b.prepare_sandbox(board,app['package'],uid,out)
        rec['desktop_activity']=rec['bms'].get('desktop_activity') or app.get('launch_activity')
        b.desktop_launch(board,dict(app,launch_activity=rec['desktop_activity']),remote,out,rec)
        started=time.monotonic();time.sleep(3)
        rec['screenshots'].append(b.capture(board,remote+'/t3.jpeg',out/'t3.jpeg'))
        time.sleep(max(0,15-(time.monotonic()-started)))
        _,ps=board.shell('ps -A -o PID,PPID,UID,NAME');(out/'processes-after.txt').write_text(ps)
        rec['observed_pids']=[r['pid'] for r in b.processes(ps) if r['uid']==uid]
        _,wm=board.shell("hidumper -s WindowManagerService -a '-a'");(out/'windows.txt').write_text(wm)
        rec['foreground']=b.foreground(wm,rec['observed_pids'])
        rec['screenshots'].append(b.capture(board,remote+'/final.jpeg',out/'final.jpeg'))
        rec['status']='captured' if rec['foreground']['confirmed'] else 'foreground_unconfirmed'
    except b.AppFailure as exc:
        rec.update(status='sandbox_prep_failed' if isinstance(exc,b.SandboxPreparationFailure) else 'app_failed',error=str(exc))
    except (b.BatchStop,KeyboardInterrupt) as exc:
        rec.update(status='batch_interrupted',error=str(exc));raise
    finally:
        if validated and uid is not None and rec['status']!='batch_interrupted':
            try:
                rec['cleanup_stopped']=b.cold_stop(board,app['package'],uid,out,'cleanup')
                if not rec['cleanup_stopped']:raise b.BatchStop('supplement cleanup unconfirmed')
            except (b.AppFailure,b.BatchStop) as exc:
                rec.update(status='batch_interrupted',error=str(exc))
        rec['finished_at']=time.time();b.save(out/'record.json',rec)
    if rec['status']=='batch_interrupted':raise b.BatchStop(rec.get('error','interrupted'))
    return rec


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--serial',required=True,choices=sorted(b.SERIALS));ap.add_argument('--keys',required=True)
    ap.add_argument('--run-id',required=True);args=ap.parse_args()
    if not b.KEY.fullmatch(args.run_id):ap.error('invalid run id')
    root=Path.home()/'a2hlab/board/bms-batch-runs'
    out=root/args.run_id/args.serial;out.mkdir(parents=True,exist_ok=False)
    board=b.Board(args.serial,str(lab_paths.tools()/'hdc_mac.sh'),
        'mac '+str(lab_paths.tools()/'board_note.sh'),'cx-t0',out/'commands')
    entries=b.load_apps(Path(__file__).with_name('apps.json'),keys=args.keys)
    board.ready();records=[]
    for i,entry in enumerate(entries):
        candidates=[]
        for p in root.glob('bms-*-20260928T175726*/'+args.serial+'/'+entry['key']+'/record.json'):
            r=json.loads(p.read_text());install=r.get('install') or {}
            if install.get('return_code')==0 and install.get('success_text'):candidates.append(p)
        if not candidates:raise b.BatchStop('no prior successful installation: '+entry['key'])
        prior=sorted(candidates)[0]
        rec=capture(board,entry,Path.home()/'a2hlab/app-inputs',out/entry['key'],
            '/data/local/tmp/bms-batch-'+args.run_id+'/'+entry['key'],prior)
        records.append(rec);b.save(out/'summary.json',{'records':records,'not_run':[a['key'] for a in entries[i+1:]],'review':'pending_review'})
        print(f'{i+1}/{len(entries)} {entry["key"]}: {rec["status"]}',flush=True)
    return 0

if __name__=='__main__':raise SystemExit(main())
